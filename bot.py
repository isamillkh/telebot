from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters
)
import random
import datetime
import sqlite3
import time
import logging
import os
import json
import asyncio

# ------ إعدادات التخزين ------ #
DB_DIR = r"D:\new new new py"
DB_PATH = os.path.join(DB_DIR, 'users.db')
RESPONSES_FILE = os.path.join(DB_DIR, 'responses.json')  # مسار ملف الردود
DAILY_GUIDANCES_FILE = os.path.join(DB_DIR, 'daily_guidances.json')  # ملف الإرشادات اليومية

# إنشاء المجلد إذا لم يكن موجوداً
os.makedirs(DB_DIR, exist_ok=True)

ADMIN_ID = 603758333 
# قائمة معرفات المجموعات المسموحة
GROUP_CHAT_IDS = [
    -1002420281280,   # المجموعة الأساسية
    -1002895336286,    # مجموعة إضافية 1
    -1001923548592,    # مجموعة إضافية 2
    -1002367464140     # مجموعة إضافية 3
]

# إعداد تسجيل الأخطاء
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ------ وظائف قاعدة البيانات ------ #
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            last_interaction TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_user(chat_id, username, first_name, last_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.datetime.now().isoformat()
    cursor.execute('''
        INSERT OR REPLACE INTO users (chat_id, username, first_name, last_name, last_interaction)
        VALUES (?, ?, ?, ?, ?)
    ''', (chat_id, username, first_name, last_name, now))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT chat_id FROM users')
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users

def remove_user(chat_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE chat_id = ?', (chat_id,))
    conn.commit()
    conn.close()

# ------ وظائف الردود ------ #
def load_responses():
    """تحميل الردود من ملف JSON أو استخدام الافتراضيات إذا لم يوجد الملف"""
    default_responses = {
        "morning_responses": [
            "صباح النور من تافتي 🌅 {user_name}",
            "صباح النور يضيء عالمك {user_name} من تافتي ✨",
            "صباح النور يملأ يومك بالطاقة الإيجابية {user_name} من تافتي 🌞"
        ],
        "evening_responses": [
            "مساء النور من تافتي 🌙 {user_name}",
            "مساء النور يكسوك بالسلام الداخلي {user_name} من تافتي ✨",
            "مساء النور يهدئ روحك {user_name} من تافتي 🌌"
        ],
        "tafti_responses": [
            "تافتي معك أينما كنت ✨ {user_name}",
            "أنا هنا لمساعدتك في رحلتك مع تافتي 🌟 {user_name}",
            "مرحبًا بك في عالم تافتي السحري 🌀 {user_name}"
        ]
    }
    
    try:
        if os.path.exists(RESPONSES_FILE):
            with open(RESPONSES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # إنشاء الملف إذا لم يكن موجوداً
            with open(RESPONSES_FILE, 'w', encoding='utf-8') as f:
                json.dump(default_responses, f, ensure_ascii=False, indent=4)
            return default_responses
    except Exception as e:
        logger.error(f"خطأ في تحميل الردود: {e}")
        return default_responses

def load_daily_guidances():
    """تحميل الإرشادات اليومية من ملف JSON"""
    default_guidances = [
        "الكون لا يستجيب لكلماتك، بل لحالتك الداخلية.\nانه يوم النور 🌿\nما تشعر به الآن يرسم واقعك القادم. ابدأ يومك بثقة وهدوء، فالعالم ينعكس كما ترى أنت.",
        "ليس عليك أن تتحكم في كل شيء. يمكنك ببساطة المراقبة والاختيار.\nانه يوم الإدراك 🌻\nالحياة ليست معركة، بل رحلة مليئة بالفرص. اختر دون مقاومة، ودع الأمور تنساب بطبيعتها.",
        # ... (جميع الإرشادات الأصلية هنا)
    ]
    
    try:
        if os.path.exists(DAILY_GUIDANCES_FILE):
            with open(DAILY_GUIDANCES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # إنشاء الملف إذا لم يكن موجوداً
            with open(DAILY_GUIDANCES_FILE, 'w', encoding='utf-8') as f:
                json.dump(default_guidances, f, ensure_ascii=False, indent=4)
            return default_guidances
    except Exception as e:
        logger.error(f"خطأ في تحميل الإرشادات اليومية: {e}")
        return default_guidances

# تحميل الردود والإرشادات عند بدء التشغيل
RESPONSES = load_responses()
DAILY_GUIDANCES = load_daily_guidances()

# ------ الكود الأصلي مع تعديلات ------ #
CATEGORIES = {
    8: "🌅 الإرشاد اليومي",
    2: "✨ كورسات للمبتدئين",
    1: "🎓 كورسات متقدمة",    
    4: "🌀 منهج ترانسيرفينغ المتكامل",
    3: "📚 مناقشات الكتب",
    5: "💬 استشارات المركز",
    6: "🧘 تأملات علاجية - المركز",
    7: "❔ المساعدة والدعم",
    9: "🎭 اختبارات شخصية مجانية"
}

COURSES = [
 # منهج ترانسيرفينغ المتكامل
    {"id": 13, "category_id": 4, "title": "🌀 باقة الوصول الأساسي", "description": "تشمل المحورين الأساسيين: إدارة الانتباه والتناغم بين العقل والقلب، وتتضمن 15 خطوة تطويرية عملية.", "price": "199$", "url": "https://tsurf-arb.com/REALTY-TRANSURFING-S4"},
    {"id": 14, "category_id": 4, "title": "🌀 باقة التطور الأعمق", "description": "تتضمن المحاور الأربعة الأولى: إدارة الانتباه، التناغم بين العقل والقلب، النية وتحقيق الهدف، التوازن الداخلي، مع 34 خطوة تطويرية.", "price": "495$", "url": "https://tsurf-arb.com/REALTY-TRANSURFING-S4"},
    {"id": 15, "category_id": 4, "title": "🌀 باقة التجربة الشاملة", "description": "تشمل المحاور الثمانية الكاملة: الانتباه، العقل والقلب، النية، التوازن، العلاقات، الصحة، المال، ومسارات التفعيل، مع 52 خطوة.", "price": "695$", "url": "https://tsurf-arb.com/REALTY-TRANSURFING-S4"},
    
    # كورسات المركز
    {"id": 1, "category_id": 1, "title": "🎯 برنامج إدارة الانتباه - Focus Plus+", "description": "ثلاث أسابيع مكثفة لإعادة وعيك وتركيزك. لمن يشعر بأنه فقد السيطرة على حياته.", "price": "مخفض لوقت محدود", "url": "https://tsurf-arb.com/lp-focus-plus-25/"},
    {"id": 2, "category_id": 1, "title": "🧠 ورشة عمل ضفيرة النوايا المطورة", "description": "تقنيات متقدمة لبناء نوايا دقيقة وتحقيق نتائج ملموسة.", "price": "49$", "url": "https://tsurf-arb.com/dafira-2025"},
    {"id": 3, "category_id": 1, "title": "🌀 تقنيات تافتي - المدرسة العليا للترانسيرفينغ", "description": "ورشة من يومين لتعلم الصيغ الفكرية وضفيرة النوايا وتقنية الانعكاس.", "price": "49$", "url": "https://tsurf-arb.com/courses/tafti-tic"},
    {"id": 4, "category_id": 1, "title": "💰 ورشة لعبة المال", "description": "ثلاث أسابيع لفهم البندولات المالية وتحرير عقلك من القيود النقدية. بقيادة سوزانا الفرا ومحمد البنا.", "price": "49$", "url": "https://tsurf-arb.com/game-of-wealth/"},

    
    # كورسات للمبتدئين (تم تغيير السعر إلى 11$)
    {"id": 6, "category_id": 2, "title": "📌 Express Transurfing", "description": "دورة تمهيدية للمبتدئين لتعلم أساسيات الترانسيرفينغ: تفعيل المراقب، إطلاق النية، ورفع الطاقة.", "price": "11$", "url": "https://tsurf-arb.com/courses/express-transurfing/"},
    {"id": 5, "category_id": 2, "title": "📜 أمسية قوانين المال", "description": "تعرف على القوانين التي تتحكم بعلاقتك مع المال. مناسبة لتغيير أنماط التفكير المالية السلبية.", "price": "21$", "url": "https://tsurf-arb.com/courses/lows-of-money"}, 
    {"id": 7, "category_id": 2, "title": "🔐 أسرار المال للجماعات السرية", "description": "مقدمة في مفاهيم الثروة والحرية المالية بأساليب مبسطة للمبتدئين.", "price": "11$", "url": "https://tsurf-arb.com/courses/secret-society/"},
    {"id": 8, "category_id": 2, "title": "🪞 القوانين المرآتية", "description": "ورشة تأسيسية تكشف كيف تصنع واقعك بعقلك وتتحكم في سيناريو حياتك.", "price": "11$", "url": "https://tsurf-arb.com/courses/realty-mirror"},
    {"id": 9, "category_id": 2, "title": "🎬 ورشة مصغرة | كتاب بروجيكتور الواقع", "description": "مقدمة عملية لكتاب 'بروجيكتور الواقع' للمبتدئين.", "price": "11$", "url": "https://tsurf-arb.com/courses/realty-mirror"},
    {"id": 30, "category_id": 2, "title": "🏃‍♂️ الحركة الفعالة للمبتدئين", "description": "تمارين تأسيسية لتحسين حركة الجسم وزيادة الطاقة الحيوية", "price": "", "links": [
        {"title": "التمارين الأساسية", "url": "https://youtu.be/2GNslhK9Mu8"},
        {"title": "تمارين الظهر للمبتدئين", "url": "https://youtu.be/XAjZSpTXEdg"},
        {"title": "تمارين الرقبة للمبتدئين", "url": "https://youtu.be/QR9RM0q51AA"}
    ]},
    
    # مناقشات الكتب
    {"id": 10, "category_id": 3, "title": "📖 كتاب ترانسيرفينغ الذات", "description": "نادي قراء أسبوعي، لقاءات تفاعلية، ترجمة لكتب نادرة", "price": "17$", "links": [
        {"title": "الأثقال | إزالة العوائق", "url": "https://youtu.be/2rubqt0UfxE"},
        {"title": "المشابك الفكرية | إزالة العوائق", "url": "https://youtu.be/rWtJhIQpIuk"},
        {"title": "كيفية إزالة الأهمية و المشبك", "url": "https://youtu.be/5-3FaLBQ_qY"},
        {"title": "مراجعة الرغبات", "url": "https://youtu.be/dpSAcym5e_0"},
        {"title": "الانضمام لمناقشة الكتاب", "url": "https://tsurf-arb.com/courses/vip-clup/"}
    ]},
    {"id": 11, "category_id": 3, "title": "📖 كتاب بروجيكتور الواقع الفردي", "description": "استكشاف لآليات تشكيل المشاهد الذهنية وتحويلها إلى واقع بديل ملموس", "price": "11$", "url": "https://tsurf-arb.com/courses/projector-tsurf/"},
    {"id": 12, "category_id": 3, "title": "🎧 كتاب صوتي - رواية الكاهنة ايتفات", "description": "رواية صوتية سريالية تكشف لك رموزًا جديدة في ذاتك", "price": "21$", "links": [
        {"title": "عطالة الزمن | الفصل الأول", "url": "https://youtu.be/rTz8xWycO10?si=PY2d05FgphqyRocb"},
        {"title": "الفتاة الاصطناعية | الفصل الثاني", "url": "https://youtu.be/lhTv_Z9LK0o"},
        {"title": "الغلاميروك المتوحشين | الفصل الثالث", "url": "https://youtu.be/O85IWXxPRwo"},
        {"title": "الحصول على النسخة الكاملة", "url": "https://tsurf-arb.com/courses/etfat/"}
    ]},
    {"id": 18, "category_id": 3, "title": "🎭 كتاب تنزه حياً باللوحة السنمائية", "description": "أول كتاب عربي لتقنيات الترانسيرفينغ المطور. تأليف: سوزانا الفرا", "price": "6.5$", "url": "https://tsurf-arb.com/product/%d9%83%d8%aa%d8%a7%d8%a8-%d8%a7%d9%84%d8%aa%d9%86%d8%b2%d9%87-%d8%ad%d9%8a%d8%a7%d9%8b-%d9%81%d9%8a-%d8%a7%d9%84%d9%84%d9%88%d8%ad%d8%a9-%d8%a7%d9%84%d8%b3%d9%8a%d9%86%d9%85%d8%a7%d8%a6%d9%8a%d8%a9/"},
    {"id": 31, "category_id": 3, "title": "✳️ سلسلة تافتي مترجمة كاملة", "description": "9 أجزاء مترجمة تغطي مفاهيم تافتي المتقدمة", "price": "مجاناً", "links": [
        {"title": "شرح تركيبة الواقع | الجزء الأول", "url": "https://youtu.be/qGOdNKMw__E"},
        {"title": "بين الششاشتين !! | الجزء الثاني", "url": "https://youtu.be/Yywh4ClNi1g"},
        {"title": "نزهة في الحلم | الجزء الثالث", "url": "https://youtu.be/rYF8QCDxcWA"},
        {"title": "أول خروج الى الواقع | الجزء الرابع", "url": "https://youtu.be/qXnD-KK_0vo"},
        {"title": "تعقب الإنتباه | الجزء الخامس", "url": "https://youtu.be/m1ijLFqmvCs"},
        {"title": "تحديد مجرى الواقع | الجزء السادس", "url": "https://youtu.be/3XEOCUUUsOE"},
        {"title": "شرح تفعيل ضفيرة تافتي | الجزء السابع", "url": "https://youtu.be/fJmRwI6VGLA"},
        {"title": "ضفيرة النوايا | خوارزمية التفعيل | الجزء الثامن", "url": "https://youtu.be/ERAwSwSeik4"},
        {"title": "الخروج من وهم الواقع | الجزء التاسع", "url": "https://youtu.be/gUvZfpgXkGU"}
    ]},
    
    # استشارات المركز
    {"id": 19, "category_id": 5, "title": "🔮 استشارة سجلات الاكاشا", "description": "استكشف سجلاتك الأكاشية لفهم مسار حياتك وتحديد معالم رحلتك الروحية", "price": "", "url": "https://tsurf-arb.com/acashic-session/"},
    {"id": 20, "category_id": 5, "title": "⚖️ استشارة التوازن النفسي", "description": "جلسات متخصصة لاستعادة التوازن النفسي وتجاوز الصدمات العاطفية", "price": "", "url": "https://tsurf-arb.com/psycology-session/"},
    {"id": 21, "category_id": 5, "title": "⏳ استشارة التنويم التراجعي", "description": "جلسات تنويم مغناطيسي للعودة إلى جذور المشكلات النفسية والروحية", "price": "", "url": "https://tsurf-arb.com/hypnosis-session/"},
    {"id": 22, "category_id": 5, "title": "🎨 اختبار تحليل الاضطرابات النفسية - لوشر", "description": "تحليل نفسي متقدم باستخدام اختبار الألوان للكشف عن التوترات والاضطرابات", "price": "", "url": "https://tsurf-arb.com/lucher-test"},
    {"id": 23, "category_id": 5, "title": "🌿 استشارة ديتوكس علاجي", "description": "برامج تطهير جسدي وروحي لتحرير الطاقة السلبية واستعادة النشاط", "price": "", "url": "https://tsurf-arb.com/detox-session/"},
    {"id": 24, "category_id": 5, "title": "🍎 استشارة تغذية علاجية وموازنة جسد", "description": "برامج تغذية متخصصة لتحقيق التوازن الجسدي وزيادة الطاقة الحيوية", "price": "", "url": "https://tsurf-arb.com/nutrition-session/"},
    
    # تأملات علاجية - المركز
    {"id": 32, "category_id": 6, "title": "🌀 تأملات علاجية", "description": "ارفع معدل اهتزازك وحقق حالة من الوعي منفصلة عن الجسد المادي", "price": "مجاناً", "links": [
        {"title": "تأمل هوبونو بونو | اعادة التناغم, الغفران", "url": "https://youtu.be/D-zOwnxNELU"},
        {"title": "تأمل رحلة الى احتمالك الافضل", "url": "https://youtu.be/HAS6Sqjdzc4"},
        {"title": "تامل التحرر من طبقات الايغو", "url": "https://youtu.be/lIhnd-q0Svw"},
        {"title": "تأمل الدرب الثوري | تقنية معايرة الحقل المغناطيسي", "url": "https://youtu.be/_9sGgKEvnzk"},
        {"title": "تأمل استعادة شظايا الروح", "url": "https://youtu.be/1OQZwEhl46o"},
        {"title": "تأمل استحقاق الحب", "url": "https://youtu.be/pu4cihwZzHk"},
        {"title": "تأمل ابتسامة من كل قلبي", "url": "https://youtu.be/pRUioeEd89s"},
        {"title": "تأمل لقاء مع مرشدك الروحي", "url": "https://youtu.be/A1_ROy1rg3c"},
        {"title": "تامل لقاء مع الروح", "url": "https://youtu.be/46khlF0tt58"}
    ]},
    
    # المساعدة والدعم
    {"id": 16, "category_id": 7, "title": "💬 التواصل المباشر - واتساب", "description": "تواصل مع فريق الدعم عبر واتساب", "price": "", "url": "https://wa.me/message/D3QAPQJRHHD6G1"},
    {"id": 33, "category_id": 7, "title": "📡 قنواتنا", "description": "تابعنا على منصات التواصل الاجتماعي", "price": "", "links": [
        {"title": "قناة اليوتيوب", "url": "https://www.youtube.com/@tsurf-arb"},
        {"title": "صفحة الفيسبوك", "url": "https://www.facebook.com/Tsurf.Arb"},
        {"title": "حساب الانستجرام", "url": "https://www.instagram.com/tsurf_arb/"},
        {"title": "قناة التلغرام", "url": "https://t.me/EXPRESS_TSURF"}
    ]},
    
    # اختبارات شخصية مجانية - الفئة الجديدة
    {"id": 34, "category_id": 9, "title": "🎬 هل أنت مخرج فيلم حياتك؟", "description": "اختبار شخصي مجاني لتحليل علاقتك مع واقعك", "price": "مجاناً", "url": "https://tsurf-arb.com/quiz-cc/"},
    {"id": 35, "category_id": 9, "title": "💰 هل يتدفق المال إلى حياتك؟", "description": "اختبار يكشف معوقات الوفرة المالية في حياتك", "price": "مجاناً", "url": "https://tsurf-arb.com/quiz-mm/"},
    {"id": 36, "category_id": 9, "title": "🔮 الحدس وتقييم اتصالك بالأنا العليا", "description": "اختبار يقيس قوة حدسك واتصالك بذاتك العليا", "price": "مجاناً", "url": "https://tsurf-arb.com/in/"}
]



# حالات المحادثة
CATEGORY, COURSE = range(2)

# ------ الدوال الأساسية للبوت ------ #
def main_menu():
    buttons = []
    ordered_categories = [8, 2, 1, 4, 3, 5, 6, 9, 7]
    for cat_id in ordered_categories:
        buttons.append([InlineKeyboardButton(CATEGORIES[cat_id], callback_data=f"cat_{cat_id}")])
    return InlineKeyboardMarkup(buttons)

def courses_menu(category_id):
    buttons = []
    for course in COURSES:
        if course["category_id"] == category_id:
            buttons.append([InlineKeyboardButton(course["title"], callback_data=f"course_{course['id']}")])
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_main")])
    return InlineKeyboardMarkup(buttons)

def course_details(course_id):
    course = next((c for c in COURSES if c["id"] == course_id), None)
    if not course:
        return None
    
    if "links" in course:
        text = f"{course['title']}\n\n"
        if course.get('description'):
            text += f"🌀 {course['description']}\n\n"
        if course.get('price'):
            text += f"💵 السعر: {course['price']}\n\n"
        text += "🔗 اختر أحد الأجزاء:"
        
        keyboard = []
        for link in course["links"]:
            keyboard.append([InlineKeyboardButton(link["title"], url=link["url"])])
        
        keyboard.append([
            InlineKeyboardButton("🔙 رجوع", callback_data=f"back_cat_{course['category_id']}"),
            InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_main")
        ])
        return text, InlineKeyboardMarkup(keyboard)
    
    if course["category_id"] in [5, 7, 9]:
        text = f"{course['title']}\n\n🌀 {course['description']}\n\n🔗 اضغط على الزر أدناه للوصول مباشرة:"
    else:
        text = f"{course['title']}\n\n🌀 {course['description']}\n\n💵 السعر: {course['price']}\n\n🔗 اضغط على الزر أدناه للوصول مباشرة:"
    
    keyboard = [
        [InlineKeyboardButton("🌐 زيارة الرابط", url=course['url'])],
        [InlineKeyboardButton("🔙 رجوع", callback_data=f"back_cat_{course['category_id']}"),
         InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_main")]
    ]
    return text, InlineKeyboardMarkup(keyboard)

async def get_daily_guidance(user_id):
    today = datetime.date.today().toordinal()
    random.seed(user_id + today)
    return random.choice(DAILY_GUIDANCES)

# ------ معالجة الأوامر والضغطات ------ #
async def show_help(message):
    help_text = "🌀 عندما تضيع في متاهات الوعي، تذكر أن هناك من ينتظر لمساعدتك:\n\n"
    keyboard = [
        [InlineKeyboardButton("💬 التواصل المباشر - واتساب", url='https://wa.me/message/D3QAPQJRHHD6G1')],
        [InlineKeyboardButton("🔙 العودة", callback_data="back_main")]
    ]
    await message.reply_text(help_text, reply_markup=InlineKeyboardMarkup(keyboard))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_help(update.message)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    user = update.effective_user
    add_user(
        chat_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    user_name = user.first_name
    welcome_message = (
        f"أهلاً بك مجدداً {user_name}، أيها المسافر في متاهات الزمن...\n\n"
        "🌌 هل تبحث عن بداية جديدة؟ أم أن الأقدار أعادتك إلى نقطة الصفر؟\n"
        "🌀 لقد أعدنا الساعة الرملية، وها أنت تعود إلى حيث بدأت رحلتك...\n\n"
        "اختر بحكمة هذه المرة، فكل اختيار قد يفتح أبواباً جديدة لم تكن تراها من قبل..."
    )
    
    await update.message.reply_text(welcome_message, reply_markup=main_menu())
    return CATEGORY

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "help":
        await show_help(query.message)
        return CATEGORY

    elif data == "back_main":
        await query.edit_message_text(text="اختر الفئة التي تريد استعراضها:", reply_markup=main_menu())
        return CATEGORY

    elif data.startswith("back_cat_"):
        cat_id = int(data.split("_")[2])
        await query.edit_message_text(
            text=f"اختر كورس من فئة: {CATEGORIES[cat_id]}",
            reply_markup=courses_menu(cat_id)
        )
        return COURSE

    elif data.startswith("cat_"):
        cat_id = int(data.split("_")[1])
        
        if cat_id == 8:
            user_id = query.from_user.id
            guidance = await get_daily_guidance(user_id)
            response = f"🌅 **إرشاد اليوم** 🌅\n\n_{guidance}_\n\nهذا الإرشاد خاص بك اليوم فقط.\nعد غداً للحصول على إرشاد جديد."
            keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_main")]]
            await query.edit_message_text(text=response, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            return CATEGORY
        
        if cat_id == 6:
            course = next((c for c in COURSES if c["id"] == 32), None)
            if not course:
                await query.answer("حدث خطأ، لم يتم العثور على التأملات")
                return COURSE
                
            text = "🌀 تأملات علاجية - المركز\n\n🔹ارفع معدل اهتزازك وحقق حالة من الوعي منفصلة عن الجسد المادي.\n\n🔸نحن كائنات متعددة الأبعاد، قادرة على تعديل أنفسنا تلقائيًا في تجارب جديدة.\n\nاختر أحد التأملات:"
            keyboard = []
            for link in course["links"]:
                keyboard.append([InlineKeyboardButton(link["title"], url=link["url"])])
            keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_main")])
            await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))
            return COURSE
        
        await query.edit_message_text(
            text=f"اختر كورس من فئة: {CATEGORIES[cat_id]}",
            reply_markup=courses_menu(cat_id)
        )
        return COURSE

    elif data.startswith("course_"):
        course_id = int(data.split("_")[1])
        course_info = course_details(course_id)
        if course_info:
            text, keyboard = course_info
            await query.edit_message_text(text=text, reply_markup=keyboard)
        return COURSE

    return CATEGORY

# وظيفة للإرسال الجماعي
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ ليس لديك صلاحية تنفيذ هذا الأمر")
        return
    
    if not context.args:
        await update.message.reply_text("📝 يرجى كتابة الرسالة بعد الأمر:\n/broadcast <الرسالة>")
        return
    
    message = " ".join(context.args)
    users = get_all_users()
    total = len(users)
    success = 0
    failed = 0
    
    await update.message.reply_text(f"🚀 بدء إرسال الرسالة إلى {total} مستخدم...")
    
    for chat_id in users:
        try:
            await context.bot.send_message(chat_id=chat_id, text=f"📬 رسالة من إدارة المركز:\n\n{message}")
            success += 1
        except Exception as e:
            logger.error(f"فشل الإرسال لـ {chat_id}: {e}")
            remove_user(chat_id)
            failed += 1
        time.sleep(0.05)
    
    report = f"✅ تم الإرسال بنجاح إلى: {success} مستخدم\n❌ فشل الإرسال إلى: {failed} مستخدم\n📊 المجموع: {total} مستخدم"
    await context.bot.send_message(chat_id=ADMIN_ID, text=report)

# وظيفة لتصدير قائمة المستخدمين
async def export_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ ليس لديك صلاحية")
        return
    
    users = get_all_users()
    users_file = os.path.join(DB_DIR, "users_list.txt")
    
    with open(users_file, 'w', encoding='utf-8') as f:
        for user in users:
            f.write(f"{user}\n")
    
    await context.bot.send_document(
        chat_id=ADMIN_ID,
        document=open(users_file, 'rb'),
        filename="users_list.txt"
    )
    await update.message.reply_text("✅ تم تصدير قائمة المستخدمين")

# وظيفة لتحديث الردود من الملف
async def reload_responses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ ليس لديك صلاحية")
        return
    
    global RESPONSES, DAILY_GUIDANCES
    try:
        RESPONSES = load_responses()
        DAILY_GUIDANCES = load_daily_guidances()
        await update.message.reply_text("✅ تم تحديث جميع الردود والإرشادات بنجاح")
    except Exception as e:
        logger.error(f"خطأ في تحديث الردود: {e}")
        await update.message.reply_text(f"❌ حدث خطأ أثناء تحديث الردود: {e}")

# وظيفة للرد على التحيات في المجموعات
async def handle_greetings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    
    # التحقق أن الرسالة في إحدى المجموعات المسموحة
    if message.chat.id not in GROUP_CHAT_IDS:
        return
    
    text = message.text.lower()
    user_name = message.from_user.first_name
    
    # الرد على صباح الخير
    if any(keyword in text for keyword in ["صباح", "صباح الخير"]):
        response = random.choice(RESPONSES["morning_responses"])
        await asyncio.sleep(5)
        await message.reply_text(response.format(user_name=user_name))
    
    # الرد على مساء الخير
    elif any(keyword in text for keyword in [ "مسا","مساء", "مساء الخير", "مساء النور"]):
        response = random.choice(RESPONSES["evening_responses"])
        await asyncio.sleep(5)
        await message.reply_text(response.format(user_name=user_name))

    # الرد على كلمة تافتي
    elif "تافتي" in text:
        response = random.choice(RESPONSES["tafti_responses"])
        await asyncio.sleep(5)
        await message.reply_text(response.format(user_name=user_name))

# ------ الدالة الرئيسية لتشغيل البوت ------ #
def main() -> None:
    # إنشاء مجلد قاعدة البيانات إذا لم يكن موجوداً
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR, exist_ok=True)
        logger.info(f"تم إنشاء مجلد قاعدة البيانات: {DB_DIR}")
    
    init_db()
    
    application = Application.builder().token("").build()
    
    # إضافة الأوامر
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("export", export_users))
    application.add_handler(CommandHandler("reload", reload_responses))
    
    # إعداد المحادثة
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CATEGORY: [CallbackQueryHandler(handle_button)],
            COURSE: [CallbackQueryHandler(handle_button)],
        },
        fallbacks=[CommandHandler("help", help_command), CommandHandler("start", start)],
        allow_reentry=True
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help_command))
    
    # معالج للرد على التحيات في المجموعات
    application.add_handler(MessageHandler(
        filters.TEXT & filters.Chat(chat_id=GROUP_CHAT_IDS),
        handle_greetings
    ))
    
    # معالج الأخطاء
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"حدث خطأ: {context.error}")
        if update.callback_query:
            await update.callback_query.answer("🌀 حدث خطأ غير متوقع... حاول مرة أخرى")
    
    application.add_error_handler(error_handler)
    
    logger.info(f"تم تهيئة قاعدة البيانات في: {DB_PATH}")
    print("🌀 البوت يعمل الآن مع قاعدة البيانات في المسار المخصص...")
    
    # إضافة معالج للرسائل العامة
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_general_messages
    ))
    
    application.run_polling()

# دالة لمعالجة الرسائل العامة
async def handle_general_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    
    # التحقق أن الرسالة في مجموعة مسموحة
    if message.chat.id not in GROUP_CHAT_IDS:
        return
    
    # يمكنك هنا إضافة ردود إضافية على كلمات مفتاحية أخرى
    text = message.text.lower()
    
    # مثال: الرد على كلمة "مساعدة"
    if "مساعدة" in text or "دعم" in text:
        await message.reply_text("يمكنك الحصول على المساعدة من خلال الضغط هنا 👉 /help")
    
    # مثال: الرد على كلمة "مرحبا"
    elif "مرحبا" in text or "اهلا" in text:
        user_name = message.from_user.first_name
        await message.reply_text(f"أهلاً بك {user_name}!\nلرؤية القائمة الرئيسية، اضغط هنا 👉 /start")

if __name__ == "__main__":
    main()
