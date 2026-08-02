"""Utility untuk mengirim email, digunakan khusus untuk mengirim kode OTP verifikasi akun."""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app


def send_otp_email(to_email, username, code, expire_minutes):
    """Mengirim kode OTP ke email pengguna lewat SMTP.

    Konfigurasi SMTP diambil dari app config: MAIL_SERVER, MAIL_PORT,
    MAIL_USE_TLS, MAIL_USERNAME, MAIL_PASSWORD, MAIL_DEFAULT_SENDER.
    """
    subject = "Kode Verifikasi OTP - Ruang Kendali"
    body_text = (
        f"Halo {username},\n\n"
        f"Kode verifikasi (OTP) akun Anda adalah: {code}\n\n"
        f"Kode ini berlaku selama {expire_minutes} menit dan hanya dapat digunakan satu kali.\n"
        "Jangan bagikan kode ini kepada siapa pun, termasuk pihak yang mengaku dari tim kami.\n\n"
        "Jika Anda tidak melakukan pendaftaran ini, abaikan email ini.\n\n"
        "Salam,\nTim Ruang Kendali - Sistem Deteksi Merokok"
    )
    body_html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto;">
        <h2 style="color:#1F4E78;">Verifikasi Akun Ruang Kendali</h2>
        <p>Halo <strong>{username}</strong>,</p>
        <p>Gunakan kode berikut untuk memverifikasi akun Anda:</p>
        <div style="font-size: 28px; font-weight: 700; letter-spacing: 6px;
                    background:#F1F5F9; padding: 14px 18px; border-radius: 8px;
                    text-align: center; margin: 16px 0;">{code}</div>
        <p>Kode berlaku selama <strong>{expire_minutes} menit</strong> dan hanya dapat
        digunakan satu kali. Jangan bagikan kode ini kepada siapa pun.</p>
        <p style="color:#666; font-size: 12px;">Jika Anda tidak melakukan pendaftaran ini,
        abaikan email ini.</p>
    </div>
    """

    sender = current_app.config['MAIL_DEFAULT_SENDER']

    msg = MIMEMultipart('alternative')
    msg['From'] = sender
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body_text, 'plain'))
    msg.attach(MIMEText(body_html, 'html'))

    mail_server = current_app.config['MAIL_SERVER']
    mail_port = current_app.config['MAIL_PORT']

    server = smtplib.SMTP(mail_server, mail_port, timeout=10)
    try:
        server.ehlo()
        if current_app.config.get('MAIL_USE_TLS'):
            server.starttls()
            server.ehlo()
        if current_app.config.get('MAIL_USERNAME'):
            server.login(current_app.config['MAIL_USERNAME'], current_app.config['MAIL_PASSWORD'])
        server.sendmail(sender, [to_email], msg.as_string())
    finally:
        server.quit()


def send_reset_password_email(to_email, username, reset_url, expire_minutes):
    """Mengirim link reset password ke email pengguna lewat SMTP."""
    subject = "Reset Kata Sandi - Ruang Kendali"
    body_text = (
        f"Halo {username},\n\n"
        "Kami menerima permintaan untuk mereset kata sandi akun Anda.\n"
        f"Buka link berikut untuk membuat kata sandi baru:\n{reset_url}\n\n"
        f"Link ini berlaku selama {expire_minutes} menit dan hanya dapat digunakan satu kali.\n\n"
        "Jika Anda tidak meminta reset kata sandi ini, abaikan email ini — kata sandi Anda tidak akan berubah.\n\n"
        "Salam,\nTim Ruang Kendali - Sistem Deteksi Merokok"
    )
    body_html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto;">
        <h2 style="color:#1F4E78;">Reset Kata Sandi</h2>
        <p>Halo <strong>{username}</strong>,</p>
        <p>Kami menerima permintaan untuk mereset kata sandi akun Anda. Klik tombol
        berikut untuk membuat kata sandi baru:</p>
        <p style="text-align:center; margin: 24px 0;">
            <a href="{reset_url}"
               style="background:#1F4E78; color:#fff; text-decoration:none; padding: 12px 24px;
                      border-radius: 6px; font-weight: 600; display: inline-block;">
                Reset Kata Sandi
            </a>
        </p>
        <p style="font-size: 12px; color:#666;">Atau salin tautan berikut ke browser Anda:<br>
        <a href="{reset_url}">{reset_url}</a></p>
        <p>Link berlaku selama <strong>{expire_minutes} menit</strong> dan hanya dapat
        digunakan satu kali.</p>
        <p style="color:#666; font-size: 12px;">Jika Anda tidak meminta reset kata sandi ini,
        abaikan email ini — kata sandi Anda tidak akan berubah.</p>
    </div>
    """

    sender = current_app.config['MAIL_DEFAULT_SENDER']

    msg = MIMEMultipart('alternative')
    msg['From'] = sender
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body_text, 'plain'))
    msg.attach(MIMEText(body_html, 'html'))

    mail_server = current_app.config['MAIL_SERVER']
    mail_port = current_app.config['MAIL_PORT']

    server = smtplib.SMTP(mail_server, mail_port, timeout=10)
    try:
        server.ehlo()
        if current_app.config.get('MAIL_USE_TLS'):
            server.starttls()
            server.ehlo()
        if current_app.config.get('MAIL_USERNAME'):
            server.login(current_app.config['MAIL_USERNAME'], current_app.config['MAIL_PASSWORD'])
        server.sendmail(sender, [to_email], msg.as_string())
    finally:
        server.quit()
