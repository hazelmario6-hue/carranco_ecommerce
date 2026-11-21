SOCIAL_LINKS = [
    {"nombre": "Facebook", "icono": "facebook-f", "url": "https://www.facebook.com/share/1YeXPURDDj/"},
    {"nombre": "X", "icono": "x-twitter", "url": "https://x.com/CarranoNoOffici"},
    {"nombre": "Instagram", "icono": "instagram", "url": "https://www.instagram.com/carranco_no_official?igsi=YmU5dnJpYjVrdzRw"},
    {"nombre": "YouTube", "icono": "youtube", "url": "https://www.youtube.com/channel/UCSG25wqzBx8TLQWX1ZLLWcQ"},
    {"nombre": "Telegram", "icono": "telegram", "url": "https://t.me/CarrancoNoOfficial"},
    {"nombre": "TikTok", "icono": "tiktok", "url": "https://www.tiktok.com/@carranconooficial?_r=1&_t=ZS-99DlRtMUglw"},
    {"nombre": "WhatsApp Business (BOT)", "icono": "whatsapp", "url": "https://wa.me/message/BP2TWQJRUBDEL1"},
]

def project_links(request):
    return {"social_links": SOCIAL_LINKS, "whatsapp_url": SOCIAL_LINKS[-1]["url"]}
