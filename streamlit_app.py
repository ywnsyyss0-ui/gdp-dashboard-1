import re
import asyncio
import logging
from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest

logging.basicConfig(level=logging.ERROR)
logging.getLogger("telethon").setLevel(logging.CRITICAL)


# =========================================================
# الإعدادات
# =========================================================

ACCOUNTS = [
    {
        "name": "مؤمل 1",
        "api_id": 35700791,
        "api_hash": "fcc5f28390dfb748501b5e08e88010f2",
        "phone": "+9647707414711"
    },
    {
        "name": "افريقي",
        "api_id": 12068932,
        "api_hash": "b73c3fd8685ed0d8bcc8fdaa39937850",
        "phone": "+573209692658"
    },
]

TARGET_CHANNEL = "taIabati"
BOT_USERNAME = "FAABOT"

# التجديد كل دقيقة
REFRESH_INTERVAL = 60

CLIENTS = []

# Lock مستقل لكل حساب
ACCOUNT_LOCKS = {}

# منع معالجة نفس الكود مرتين
SEEN_CODES = set()


# =========================================================
# أدوات الأزرار
# =========================================================

async def find_and_click(client, button_text, limit=3):
    """
    البحث في آخر رسائل البوت عن زر معين ثم الضغط عليه.
    """
    messages = await client.get_messages(
        BOT_USERNAME,
        limit=limit
    )

    for message in messages:

        if not message.buttons:
            continue

        for row in message.buttons:

            for button in row:

                text = button.text or ""

                if button_text in text:

                    await button.click()

                    return True

    return False


# =========================================================
# الاشتراك بالقنوات المطلوبة
# =========================================================

async def check_and_join_channels(
    client,
    account_name,
    response
):
    if not response:
        return False

    text = response.text or ""

    if (
        "لطفاً عليك الاشتراك" not in text
        and "غير مشترك" not in text
    ):
        return False

    print(
        f"[{account_name}] ⚠️ "
        f"البوت يطلب الاشتراك"
    )

    if not response.buttons:
        return False

    joined = False

    for row in response.buttons:

        for button in row:

            if not button.url:
                continue

            try:

                url = button.url

                # القنوات العامة فقط
                if "t.me/" not in url:
                    continue

                username = (
                    url.split("/")[-1]
                    .split("?")[0]
                )

                if username.startswith("+"):
                    continue

                await client(
                    JoinChannelRequest(username)
                )

                joined = True

                print(
                    f"[{account_name}] 🟢 "
                    f"تم الاشتراك: @{username}"
                )

            except Exception:
                pass

    return joined


# =========================================================
# تشغيل البوت
# =========================================================

async def initialize_bot_start(
    client,
    account_name
):
    try:

        async with client.conversation(
            BOT_USERNAME,
            timeout=10
        ) as conv:

            await conv.send_message("/start")

            response = await conv.get_response()

            joined = await check_and_join_channels(
                client,
                account_name,
                response
            )

            if joined:

                await asyncio.sleep(0)

                await conv.send_message("/start")

                try:
                    await conv.get_response()
                except Exception:
                    pass

        print(
            f"[{account_name}] ✅ "
            f"القائمة الرئيسية جاهزة"
        )

        return True

    except Exception as e:

        print(
            f"[{account_name}] ⚠️ "
            f"خطأ /start: {e}"
        )

        return False


# =========================================================
# تجهيز وضع استخدام الكود
# =========================================================

async def prepare_code_mode(
    client,
    account_name
):
    try:

        clicked = await find_and_click(
            client,
            "استخدام كود"
        )

        if clicked:

            print(
                f"[{account_name}] ⚡ "
                f"جاهز لاستقبال الكود"
            )

            return True

        # إذا لم نجد الزر
        await client.send_message(
            BOT_USERNAME,
            "/start"
        )

        await asyncio.sleep(0)

        clicked = await find_and_click(
            client,
            "استخدام كود"
        )

        if clicked:

            print(
                f"[{account_name}] ⚡ "
                f"تم الدخول إلى وضع الكود"
            )

            return True

    except Exception as e:

        print(
            f"[{account_name}] ⚠️ "
            f"فشل التجهيز: {e}"
        )

    return False


# =========================================================
# التجديد كل دقيقة
# رجوع -> استخدام كود
# =========================================================

async def refresh_code_mode(
    client,
    account_name
):
    lock = ACCOUNT_LOCKS[account_name]

    while True:

        try:

            await asyncio.sleep(
                REFRESH_INTERVAL
            )

            # لا نجدد أثناء إرسال كود
            async with lock:

                print(
                    f"[{account_name}] 🔄 "
                    f"تجديد وضع الكود..."
                )

                # ---------------------------------
                # 1. رجوع
                # ---------------------------------

                back = await find_and_click(
                    client,
                    "رجوع"
                )

                if not back:

                    print(
                        f"[{account_name}] ⚠️ "
                        f"لم أجد زر رجوع"
                    )

                    # محاولة إصلاح الحالة
                    await initialize_bot_start(
                        client,
                        account_name
                    )

                    await prepare_code_mode(
                        client,
                        account_name
                    )

                    continue

                print(
                    f"[{account_name}] ↩️ رجوع"
                )

                # انتظار قصير لوصول القائمة
                await asyncio.sleep(0)

                # ---------------------------------
                # 2. استخدام كود
                # ---------------------------------

                code_button = (
                    await find_and_click(
                        client,
                        "استخدام كود"
                    )
                )

                if code_button:

                    print(
                        f"[{account_name}] ⚡ "
                        f"تم تجديد وضع الكود"
                    )

                else:

                    # محاولة ثانية قصيرة
                    await asyncio.sleep(0)

                    code_button = (
                        await find_and_click(
                            client,
                            "استخدام كود"
                        )
                    )

                    if code_button:

                        print(
                            f"[{account_name}] ⚡ "
                            f"جاهز للكود القادم"
                        )

                    else:

                        print(
                            f"[{account_name}] ⚠️ "
                            f"لم أجد استخدام كود"
                        )

        except asyncio.CancelledError:
            break

        except Exception as e:

            print(
                f"[{account_name}] ⚠️ "
                f"خطأ التجديد: {e}"
            )

            await asyncio.sleep(0)


# =========================================================
# فحص نتيجة الكود
# =========================================================

async def check_result(
    client,
    account_name,
    code
):
    try:

        await asyncio.sleep(0)

        messages = await client.get_messages(
            BOT_USERNAME,
            limit=1
        )

        if not messages:
            return

        text = messages[0].text or ""

        match = re.search(
            r"(\d+)\s*نقطة",
            text
        )

        if match:

            points = match.group(1)

            print(
                f"[{account_name}] 🎉 "
                f"{code} -> +{points} نقطة"
            )

        else:

            first_line = (
                text.splitlines()[0]
                if text
                else "بدون رد"
            )

            print(
                f"[{account_name}] 📩 "
                f"{first_line}"
            )

    except Exception as e:

        print(
            f"[{account_name}] ⚠️ "
            f"فحص الرد: {e}"
        )


# =========================================================
# إرسال الكود
# =========================================================

async def send_code_fast(
    client,
    account_name,
    code
):
    lock = ACCOUNT_LOCKS[account_name]

    try:

        async with lock:

            # الحساب يفترض أنه موجود مسبقاً
            # داخل وضع إدخال الكود

            await client.send_message(
                BOT_USERNAME,
                code
            )

            print(
                f"[{account_name}] 🚀 "
                f"أرسل: {code}"
            )

        # قراءة النتيجة لا تؤخر الحسابات الأخرى
        asyncio.create_task(
            check_result(
                client,
                account_name,
                code
            )
        )

    except Exception as e:

        print(
            f"[{account_name}] ❌ "
            f"فشل إرسال {code}: {e}"
        )


# =========================================================
# تشغيل الحساب
# =========================================================

async def start_account(account):

    account_name = account["name"]

    session_name = (
        f"session_name{account['phone']}"
    )

    client = TelegramClient(
        session_name,
        int(account["api_id"]),
        account["api_hash"],
        auto_reconnect=True,
        connection_retries=None,
        retry_delay=1
    )

    try:

        await client.start(
            phone=account["phone"]
        )

        print(
            f"[✓] تم تسجيل الدخول: "
            f"{account_name}"
        )

        # Lock للحساب
        ACCOUNT_LOCKS[account_name] = (
            asyncio.Lock()
        )

        # تشغيل البوت
        await initialize_bot_start(
            client,
            account_name
        )

        # الدخول إلى استخدام كود
        await prepare_code_mode(
            client,
            account_name
        )

        CLIENTS.append(
            (
                client,
                account_name
            )
        )

        # بدء التجديد كل دقيقة
        asyncio.create_task(
            refresh_code_mode(
                client,
                account_name
            )
        )

        return client

    except Exception as e:

        print(
            f"[{account_name}] ❌ "
            f"فشل تسجيل الدخول: {e}"
        )

        try:
            await client.disconnect()
        except Exception:
            pass

        return None


# =========================================================
# MAIN
# =========================================================

async def main():

    CLIENTS.clear()
    ACCOUNT_LOCKS.clear()

    print(
        "\n"
        "====================================\n"
        "⚡ TELEGRAM CODE LISTENER\n"
        "====================================\n"
    )

    # تشغيل جميع الحسابات معاً
    results = await asyncio.gather(
        *(
            start_account(account)
            for account in ACCOUNTS
        )
    )

    active = [
        x
        for x in results
        if x is not None
    ]

    if not active:

        print(
            "❌ لا يوجد حساب متصل"
        )

        return

    # أول حساب يستمع للقناة
    listener_client, listener_name = (
        CLIENTS[0]
    )

    print(
        f"\n🎯 حساب الالتقاط: "
        f"{listener_name}"
    )

    print(
        f"📡 القناة: "
        f"@{TARGET_CHANNEL}"
    )

    print(
        f"👥 الحسابات: "
        f"{len(CLIENTS)}"
    )

    print(
        "🔄 التجديد: كل 60 ثانية"
    )

    print(
        "\n⚡ انتظار الكود...\n"
    )

    # =====================================================
    # التقاط الأكواد
    # =====================================================

    @listener_client.on(
        events.NewMessage(
            chats=TARGET_CHANNEL
        )
    )
    async def code_listener(event):

        try:

            text = (
                event.raw_text
                .replace("\xa0", " ")
                .replace("\u200b", "")
                .replace("\u200c", "")
                .replace("\u200d", "")
                .strip()
            )

            if "2000" not in text:
            	return
            match = re.search(
                r"(?:الكود|كود|code)"
                r"\s*[:：\-]?\s*"
                r"([A-Za-z0-9]+)",
                text,
                re.IGNORECASE
            )

            if not match:
                return

            code = match.group(1).strip()

            # منع نفس الكود من التنفيذ مرتين
            if code in SEEN_CODES:
                return

            SEEN_CODES.add(code)

            if len(SEEN_CODES) > 100:
                SEEN_CODES.clear()
                SEEN_CODES.add(code)

            print(
                "\n"
                "===================================="
            )

            print(
                f"🚨 تم التقاط: {code}"
            )

            print(
                f"⚡ الإرسال إلى "
                f"{len(CLIENTS)} حساب"
            )

            # إطلاق جميع عمليات الإرسال
            # بدون انتظار حساب ثم الآخر
            for client, name in CLIENTS:

                asyncio.create_task(
                    send_code_fast(
                        client,
                        name,
                        code
                    )
                )

        except Exception as e:

            print(
                f"❌ خطأ الالتقاط: {e}"
            )

    # إبقاء الحسابات متصلة
    await asyncio.gather(
        *(
            client.run_until_disconnected()
            for client, _ in CLIENTS
        )
    )


# =========================================================
# إعادة التشغيل عند انقطاع الاتصال
# =========================================================

if __name__ == "__main__":

    while True:

        try:

            asyncio.run(
                main()
            )

        except KeyboardInterrupt:

            print(
                "\n🛑 تم الإيقاف يدوياً"
            )

            break

        except Exception as e:

            print(
                f"\n⚠️ خطأ/انقطاع اتصال: {e}"
            )

            print(
                "🔄 إعادة التشغيل بعد ثانيتين..."
            )

            import time
            time.sleep(0)    # - GDP for 1962
    # - ...
    # - GDP for 2022
    #
    # ...but I want this instead:
    # - Country Name
    # - Country Code
    # - Year
    # - GDP
    #
    # So let's pivot all those year-columns into two: Year and GDP
    gdp_df = raw_gdp_df.melt(
        ['Country Code'],
        [str(x) for x in range(MIN_YEAR, MAX_YEAR + 1)],
        'Year',
        'GDP',
    )

    # Convert years from string to integers
    gdp_df['Year'] = pd.to_numeric(gdp_df['Year'])

    return gdp_df

gdp_df = get_gdp_data()

# -----------------------------------------------------------------------------
# Draw the actual page

# Set the title that appears at the top of the page.
'''
# :earth_americas: GDP dashboard

Browse GDP data from the [World Bank Open Data](https://data.worldbank.org/) website. As you'll
notice, the data only goes to 2022 right now, and datapoints for certain years are often missing.
But it's otherwise a great (and did I mention _free_?) source of data.
'''

# Add some spacing
''
''

min_value = gdp_df['Year'].min()
max_value = gdp_df['Year'].max()

from_year, to_year = st.slider(
    'Which years are you interested in?',
    min_value=min_value,
    max_value=max_value,
    value=[min_value, max_value])

countries = gdp_df['Country Code'].unique()

if not len(countries):
    st.warning("Select at least one country")

selected_countries = st.multiselect(
    'Which countries would you like to view?',
    countries,
    ['DEU', 'FRA', 'GBR', 'BRA', 'MEX', 'JPN'])

''
''
''

# Filter the data
filtered_gdp_df = gdp_df[
    (gdp_df['Country Code'].isin(selected_countries))
    & (gdp_df['Year'] <= to_year)
    & (from_year <= gdp_df['Year'])
]

st.header('GDP over time', divider='gray')

''

st.line_chart(
    filtered_gdp_df,
    x='Year',
    y='GDP',
    color='Country Code',
)

''
''


first_year = gdp_df[gdp_df['Year'] == from_year]
last_year = gdp_df[gdp_df['Year'] == to_year]

st.header(f'GDP in {to_year}', divider='gray')

''

cols = st.columns(4)

for i, country in enumerate(selected_countries):
    col = cols[i % len(cols)]

    with col:
        first_gdp = first_year[first_year['Country Code'] == country]['GDP'].iat[0] / 1000000000
        last_gdp = last_year[last_year['Country Code'] == country]['GDP'].iat[0] / 1000000000

        if math.isnan(first_gdp):
            growth = 'n/a'
            delta_color = 'off'
        else:
            growth = f'{last_gdp / first_gdp:,.2f}x'
            delta_color = 'normal'

        st.metric(
            label=f'{country} GDP',
            value=f'{last_gdp:,.0f}B',
            delta=growth,
            delta_color=delta_color
        )
