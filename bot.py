import asyncio
import logging
import random
import string
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import FSInputFile
from aiogram.client.default import DefaultBotProperties

# KONFIGURASI BOT
TOKEN = "7849802829:AAHQccY_3ckpSrEmnfN1FtMK1ogCf48IFzA"
ADMIN_ID = 5453749122
QRIS_IMAGE_PATH = "qris_image.png"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ================== DATABASE SETUP ==================
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
            jumlah INTEGER,
            kode_unik TEXT NOT NULL,
            status TEXT DEFAULT 'PENDING'
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ================== FUNGSI UTAMA ==================
def generate_kode_unik():
    return "N" + "".join(random.choices(string.digits, k=5))

# ================== FITUR PEMBELI ==================
@dp.message(Command("produk"))
async def lihat_produk(message: types.Message):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM produk")
    produk = cursor.fetchall()
    conn.close()

    if not produk:
        await message.answer("❌ <b>Belum ada produk yang tersedia.</b>")
        return

    text = "<b>📦 Daftar Produk:</b>\n\n"
    for p in produk:
        # Ganti underscore dengan spasi pada nama produk
        nama = p[1].replace("_", " ")
        text += f"🆔 <b>ID:</b> <code>{p[0]}</code>\n" \
                f"📌 <b>Nama:</b> {nama}\n" \
                f"💰 <b>Harga:</b> Rp {p[2]}\n" \
                f"📦 <b>Stok:</b> {p[3]}\n" \
                "-----------------------------\n"
    await message.answer(text)

@dp.message(Command("beli"))
async def beli_produk(message: types.Message):
    try:
        # Cek apakah pembeli sudah memiliki order pending
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, produk_id, jumlah, kode_unik FROM transaksi WHERE pembeli_id = ? AND status = 'pending'",
            (message.from_user.id,)
        )
        existing = cursor.fetchone()
        if existing:
            transaksi_id, produk_id, jumlah, kode_unik = existing
            cursor.execute("SELECT nama, harga FROM produk WHERE id = ?", (produk_id,))
            produk = cursor.fetchone()
            conn.close()
            if produk:
                total_harga = produk[1] * jumlah
                text = (
                    f"⚠️ Anda memiliki transaksi yang belum dibayar!\n\n"
                    f"🆔 ID Transaksi: <code>{transaksi_id}</code>\n"
                    f"🔑 Kode Unik: <code>{kode_unik}</code>\n"
                    f"📌 Produk: {produk[0].replace('_', ' ')}\n"
                    f"🔢 Jumlah: {jumlah}\n"
                    f"💵 Total Harga: {total_harga}\n\n"
                    "Silakan lakukan pembayaran dengan <code>/bayar</code>."
                )
                return await message.answer(text)
            else:
                conn.close()
                return await message.answer("⚠️ Transaksi sebelumnya ditemukan. Silakan konfirmasi pembayaran terlebih dahulu.")
        
        # Jika tidak ada order pending, proses order baru
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            return await message.answer("⚠️ Format salah! Gunakan: <code>/beli &lt;produk_id&gt; &lt;kuantitas&gt;</code>")
        _, produk_id, kuantitas = parts
        produk_id = int(produk_id)
        kuantitas = int(kuantitas)

        cursor.execute("SELECT nama, harga, stok FROM produk WHERE id = ?", (produk_id,))
        produk = cursor.fetchone()

        if not produk:
            conn.close()
            return await message.answer("❌ Produk tidak ditemukan!")
        if produk[2] < kuantitas:
            conn.close()
            return await message.answer("⚠️ Stok tidak cukup!")
        
        total_harga = produk[1] * kuantitas
        kode_unik = generate_kode_unik()

        cursor.execute("""
            INSERT INTO transaksi (pembeli_id, produk_id, jumlah, kode_unik, status) 
            VALUES (?, ?, ?, ?, ?)
        """, (message.from_user.id, produk_id, kuantitas, kode_unik, "pending"))
        conn.commit()
        conn.close()

        text = (
            f"✅ Pesanan berhasil dibuat!\n\n"
            f"📌 Produk: <b>{produk[0].replace('_', ' ')}</b>\n"
            f"🔢 Jumlah: <b>{kuantitas}</b>\n"
            f"💰 Total Harga: <b>Rp {total_harga}</b>\n"
            f"🔑 Kode Unik: <b>{kode_unik}</b>\n\n"
            "Silakan lakukan pembayaran dengan /bayar dan masukkan nominal sesuai harga di atas."
        )
        await message.answer(text)
    except Exception as e:
        await message.answer("⚠️ Format salah! Gunakan: <code>/beli &lt;produk_id&gt; &lt;kuantitas&gt;</code>")

@dp.message(Command("bayar"))
async def detail_pembayaran(message: types.Message):
    # Untuk menampilkan detail transaksi pembeli (jika ada)
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT t.id, t.kode_unik, t.jumlah, p.nama, p.harga FROM transaksi t JOIN produk p ON t.produk_id = p.id WHERE t.pembeli_id = ? AND t.status = 'pending'", 
                   (message.from_user.id,))
    transaksi = cursor.fetchall()
    conn.close()

    if not transaksi:
        await message.answer("❌ <b>Kamu belum memiliki transaksi!</b>")
        return

    text = "<b>🔖 Detail Pembayaran Anda:</b>\n\n"
    for t in transaksi:
        total = t[4] * t[2]
        text += (
            f"🆔 <b>ID Transaksi:</b> <code>{t[0]}</code>\n"
            f"🔑 <b>Kode Unik:</b> <code>{t[1]}</code>\n"
            f"📌 <b>Produk:</b> {t[3].replace('_', ' ')}\n"
            f"🔢 <b>Jumlah:</b> {t[2]}\n"
            f"💵 <b>Total Harga:</b> {total}\n"
            "-----------------------------\n"
        )
    text += "<b>Silakan transfer ke QRIS berikut:</b>"
    await message.answer(text)
    qris_image = FSInputFile(QRIS_IMAGE_PATH)
    await message.answer_photo(qris_image)

# ================== FITUR ADMIN ==================
@dp.message(Command("tambahproduk"))
async def tambah_produk(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("❌ <b>Hanya admin yang dapat menambahkan produk.</b>")

    try:
        # Format: /tambahproduk <nama> <harga> <stok>
        cmd_args = message.text.split(maxsplit=3)  
        
        if len(cmd_args) < 4:
            return await message.answer("⚠️ <b>Format salah!</b>\nGunakan: <code>/tambahproduk &lt;nama&gt; &lt;harga&gt; &lt;stok&gt;</code>")

        _, nama, harga, stok = cmd_args
        harga, stok = int(harga), int(stok)

        # Simpan ke database
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO produk (nama, harga, stok) VALUES (?, ?, ?)", (nama, harga, stok))
        conn.commit()
        conn.close()

        await message.answer(f"✅ <b>Produk berhasil ditambahkan!</b>\n📌 Nama: {nama}\n💰 Harga: {harga}\n📦 Stok: {stok}")

    except ValueError:
        await message.answer("⚠️ <b>Harga dan stok harus berupa angka!</b>\nGunakan: <code>/tambahproduk &lt;nama&gt; &lt;harga&gt; &lt;stok&gt;</code>")

    except Exception as e:
        await message.answer("❌ <b>Terjadi kesalahan!</b> Periksa kembali formatnya atau coba lagi nanti.")
        print(f"Error: {e}")  # Untuk debugging jika ada error

@dp.message(Command("editproduk"))
async def edit_produk(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ <b>Hanya admin yang bisa mengedit produk.</b>")
        return
    try:
        # Format: /editproduk <produk_id> <harga> <stok>
        _, produk_id, harga, stok = message.text.split(" ", 3)
        produk_id, harga, stok = int(produk_id), int(harga), int(stok)
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE produk SET harga = ?, stok = ? WHERE id = ?", (harga, stok, produk_id))
        conn.commit()
        conn.close()
        await message.answer(f"✅ Produk ID <b>{produk_id}</b> berhasil diperbarui!")
    except:
        await message.answer("⚠️ <b>Format salah!</b>\nGunakan: <code>/editproduk &lt;produk_id&gt; &lt;harga&gt; &lt;stok&gt;</code>")

@dp.message(Command("hapus"))
async def hapus_produk(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("❌ <b>Hanya admin yang dapat menghapus produk.</b>")
    try:
        # Format: /hapus <produk_id>
        _, produk_id = message.text.split(maxsplit=1)
        produk_id = int(produk_id)
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM produk WHERE id = ?", (produk_id,))
        conn.commit()
        conn.close()
        await message.answer(f"✅ Produk dengan ID <b>{produk_id}</b> berhasil dihapus!")
    except:
        await message.answer("⚠️ <b>Format salah!</b>\nGunakan: <code>/hapus &lt;produk_id&gt;</code>")

@dp.message(Command("cektransaksi"))
async def cek_transaksi(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("❌ <b>Hanya admin yang bisa mengecek transaksi!</b>")
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.id, t.pembeli_id, p.nama, t.kode_unik, t.status, t.jumlah
        FROM transaksi t
        JOIN produk p ON t.produk_id = p.id
        WHERE t.status = 'pending'
    """)
    transaksi = cursor.fetchall()
    conn.close()
    if not transaksi:
        return await message.answer("📭 <b>Tidak ada transaksi pending!</b>")
    text = "<b>📋 Daftar Transaksi Pending:</b>\n"
    for t in transaksi:
        total = t[5] * int(cursor.execute("SELECT harga FROM produk WHERE id = ?", (t[2],)).fetchone()[0]) if False else ""
        text += (
            f"🆔 <b>ID:</b> <code>{t[0]}</code>\n"
            f"👤 <b>User ID:</b> <code>{t[1]}</code>\n"
            f"📌 <b>Produk:</b> {t[2].replace('_', ' ')}\n"
            f"🔢 <b>Jumlah:</b> {t[5]}\n"
            f"🔑 <b>Kode Unik:</b> <code>{t[3]}</code>\n"
            f"⏳ <b>Status:</b> {t[4]}\n"
            "-----------------------------\n"
        )
    await message.answer(text)

@dp.message(Command("konfirmasi"))
async def konfirmasi_pembayaran(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("❌ <b>Hanya admin yang bisa mengonfirmasi pembayaran!</b>")
    try:
        # Format: /konfirmasi <kode_unik> <username> <password>
        _, kode_unik, username, password = message.text.split(maxsplit=3)
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT pembeli_id, jumlah, produk_id FROM transaksi WHERE kode_unik = ? AND status = 'pending'", (kode_unik,))
        transaksi = cursor.fetchone()
        if not transaksi:
            return await message.answer("❌ <b>Transaksi tidak ditemukan atau sudah dikonfirmasi!</b>")
        pembeli_id, jumlah, produk_id = transaksi
        # Update status transaksi menjadi 'confirmed'
        cursor.execute("UPDATE transaksi SET status = 'confirmed' WHERE kode_unik = ?", (kode_unik,))
        cursor.execute("UPDATE produk SET stok = stok - ? WHERE id = ?", (jumlah, produk_id))
        conn.commit()
        conn.close()
        pesan_pembeli = (
            f"🎉 <b>Pembayaran Dikonfirmasi!</b>\n\n"
            f"🔑 <b>Username:</b> <code>{username}</code>\n"
            f"🔒 <b>Password:</b> <code>{password}</code>\n\n"
            "✅ Silakan login menggunakan data di atas, Terima kasih!"
        )
        await bot.send_message(pembeli_id, pesan_pembeli)
        await message.answer(f"✅ <b>Transaksi dengan kode <code>{kode_unik}</code> berhasil dikonfirmasi!</b>")
    except:
        await message.answer("⚠️ <b>Format salah!</b>\nGunakan: <code>/konfirmasi &lt;kode_unik&gt; &lt;username&gt; &lt;password&gt;</code>")

# FITUR TERIMA GAMBAR (Bukti Pembayaran) - Auto-forward ke admin dengan informasi transaksi
@dp.message(lambda message: message.photo)
async def terima_gambar(message: types.Message):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, kode_unik FROM transaksi WHERE pembeli_id = ? AND status = 'pending'", (message.from_user.id,))
    transaksi = cursor.fetchone()
    conn.close()
    if not transaksi:
        return await message.answer("⚠️ <b>Kamu tidak memiliki transaksi pending!</b>")
    transaksi_id, kode_unik = transaksi
    notif = (
        f"📸 <b>Bukti pembayaran diterima!</b>\n"
        f"🆔 <b>ID Transaksi:</b> <code>{transaksi_id}</code>\n"
        f"🔑 <b>Kode Unik:</b> <code>{kode_unik}</code>\n"
        f"👤 Dari User: <b>{message.from_user.id}</b>"
    )
    await bot.send_message(ADMIN_ID, notif)
    await bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
    await message.answer("📩 <b>Bukti pembayaran telah dikirim ke admin. Mohon tunggu konfirmasi!</b>")

# FITUR HELP - Menampilkan semua perintah yang tersedia
@dp.message(Command("help"))
async def bantuan(message: types.Message):
    help_text = (
        "<b>Daftar Perintah Bot:</b>\n\n"
        "<code>/produk</code> - Melihat daftar produk\n"
        "<code>/tambahproduk &lt;nama&gt; &lt;harga&gt; &lt;stok&gt;</code> - Menambah produk (admin)\n"
        "<code>/editproduk &lt;produk_id&gt; &lt;harga&gt; &lt;stok&gt;</code> - Mengedit produk (admin)\n"
        "<code>/hapus &lt;produk_id&gt;</code> - Menghapus produk (admin)\n"
        "<code>/beli &lt;produk_id&gt; &lt;kuantitas&gt;</code> - Membeli produk\n"
        "<code>/bayar</code> - Melihat detail pembayaran transaksi pending\n"
        "<code>/cektransaksi</code> - Melihat transaksi pending (admin)\n"
        "<code>/konfirmasi &lt;kode_unik&gt; &lt;username&gt; &lt;password&gt;</code> - Konfirmasi pembayaran (admin)\n"
        "<code>/help</code> - Menampilkan daftar perintah\n"
    )
    await message.answer(help_text)

# FITUR HAPUS PRODUK (Admin)
@dp.message(Command("hapus"))
async def hapus_produk(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("❌ <b>Hanya admin yang dapat menghapus produk.</b>")
    try:
        _, produk_id = message.text.split(maxsplit=1)
        produk_id = int(produk_id)
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM produk WHERE id = ?", (produk_id,))
        conn.commit()
        conn.close()
        await message.answer(f"✅ Produk dengan ID <b>{produk_id}</b> berhasil dihapus!")
    except:
        await message.answer("⚠️ <b>Format salah!</b>\nGunakan: <code>/hapus &lt;produk_id&gt;</code>")

# Print status agar terlihat bot sudah berjalan
async def main():
    print("🤖 Bot telah berjalan...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
