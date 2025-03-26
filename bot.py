import sqlite3
import random
import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile

TOKEN = "7849802829:AAHQccY_3ckpSrEmnfN1FtMK1ogCf48IFzA"
ADMIN_ID = 5453749122
QRIS_IMAGE_PATH = "qris_image.png"

bot = Bot(token=TOKEN)
dp = Dispatcher()

def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produk (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT NOT NULL,
            harga INTEGER NOT NULL,
            stok INTEGER NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transaksi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pembeli_id INTEGER NOT NULL,
            produk_id INTEGER NOT NULL,
            kode_unik TEXT NOT NULL,
            status TEXT DEFAULT 'PENDING'
        )
    """)
    conn.commit()
    conn.close()

init_db()

# FUNGSI KODE UNIK
def generate_kode_unik():
    return f"N{random.randint(1000, 9999)}"

# FITUR TAMBAH PRODUK
@dp.message(Command("tambahproduk"))
async def tambah_produk(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("🚫 Hanya admin yang bisa menambah produk!")

    try:
        _, nama, harga, stok = message.text.split(maxsplit=3)
        harga, stok = int(harga), int(stok)

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO produk (nama, harga, stok) VALUES (?, ?, ?)", (nama, harga, stok))
        conn.commit()
        conn.close()

        await message.answer(f"✅ Produk **{nama}** berhasil ditambahkan!\n💰 Harga: {harga}\n📦 Stok: {stok}")
    except:
        await message.answer("⚠️ Format salah! Gunakan: `/tambahproduk <nama> <harga> <stok>`")

# FITUR BELI
@dp.message(Command("beli"))
async def beli_produk(message: types.Message):
    try:
        _, produk_id = message.text.split(maxsplit=1)
        produk_id = int(produk_id)

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT nama, harga, stok FROM produk WHERE id = ?", (produk_id,))
        produk = cursor.fetchone()

        if not produk:
            return await message.answer("❌ Produk tidak ditemukan!")

        if produk[2] <= 0:
            return await message.answer("⚠️ Produk ini sedang **habis stok**!")

        kode_unik = generate_kode_unik()
        cursor.execute("INSERT INTO transaksi (pembeli_id, produk_id, kode_unik) VALUES (?, ?, ?)",
                       (message.from_user.id, produk_id, kode_unik))
        conn.commit()
        conn.close()

        qris_image = FSInputFile(QRIS_IMAGE_PATH)
        await bot.send_photo(message.chat.id, qris_image, caption=f"""
🛒 Detail Pembelian
📌 Produk: {produk[0]}
💰 Harga: {produk[1]}
🔢 Kode Unik: {kode_unik}
📸 Kirim bukti pembayaran setelah transfer!
        """)

    except:
        await message.answer("⚠️ Format salah! Gunakan: `/beli <produk_id>`")

# FITUR CEK TRANSAKSI
@dp.message(Command("cektransaksi"))
async def cek_transaksi(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("🚫 Hanya admin yang bisa mengecek transaksi!")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.id, t.pembeli_id, p.nama, t.kode_unik, t.status
        FROM transaksi t
        JOIN produk p ON t.produk_id = p.id
    """)
    transaksi = cursor.fetchall()
    conn.close()

    if not transaksi:
        return await message.answer("📭 Tidak ada transaksi pending!")

    text = "**📋 Daftar Transaksi Pending:**\n"
    for t in transaksi:
        text += f"""
🆔 ID: `{t[0]}`
👤 User ID: `{t[1]}`
📌 Produk: {t[2]}
🔢 Kode Unik: `{t[3]}`
📍 Status: **{t[4]}**\n"""

    await message.answer(text)

# FITUR KONFIRMASI
@dp.message(Command("konfirmasi"))
async def konfirmasi_transaksi(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("🚫 Hanya admin yang bisa konfirmasi pembayaran!")

    try:
        _, transaksi_id, username, password = message.text.split(maxsplit=3)

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT pembeli_id FROM transaksi WHERE id = ? AND status = 'PENDING'", (transaksi_id,))
        transaksi = cursor.fetchone()

        if not transaksi:
            return await message.answer("❌ Transaksi tidak ditemukan atau sudah dikonfirmasi!")

        cursor.execute("UPDATE transaksi SET status = 'LUNAS' WHERE id = ?", (transaksi_id,))
        conn.commit()
        conn.close()

        pembeli_id = transaksi[0]
        pesan_pembeli = f"""
🎉 Pembayaran Berhasil!
🆔 ID Transaksi: `{transaksi_id}`
👤 Username: `{username}`
🔑 Password: `{password}`
✅ Silakan login menggunakan data di atas!
        """

        await bot.send_message(pembeli_id, pesan_pembeli)
        await message.answer(f"✅ Transaksi `{transaksi_id}` berhasil dikonfirmasi!")

    except:
        await message.answer("⚠️ Format salah! Gunakan: `/konfirmasi <transaksi_id> <username> <password>`")

# FITUR TERIMA GAMBAR
@dp.message(lambda message: message.photo)
async def terima_gambar(message: types.Message):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM transaksi WHERE pembeli_id = ? AND status = 'PENDING'", (message.from_user.id,))
    transaksi = cursor.fetchone()
    conn.close()

    if not transaksi:
        return await message.answer("⚠️ Kamu tidak punya transaksi yang pending!")

    await bot.send_message(ADMIN_ID, f"📸 **Bukti pembayaran dari User {message.from_user.id}**\n🔍 Cek dan konfirmasi segera!")
    await bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)

async def main():
    await dp.start_polling(bot)
    print ("Bot sudah berjalan...")

if __name__ == "__main__":
    asyncio.run(main())