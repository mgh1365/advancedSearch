import streamlit as st
import pandas as pd
from rapidfuzz import fuzz
import os
import glob

# مسیرهای فایل برای نسخه وب
# این فایل‌ها باید در ریپازیتوری گیت‌هاب شما و در کنار همین فایل پایتون قرار داشته باشند
PRICING_FILE = "Pricing algo.xlsm"
PRICING_SHEET = "Pricing"
EXPORTED_FOLDER = "Exported_Files" # پوشه ای که فایل های اکسپورت شده در آن قرار می گیرند

EN_TO_FA = {
'q':'ض','w':'ص','e':'ث','r':'ق','t':'ف','y':'غ','u':'ع','i':'ه','o':'خ','p':'ح','[':'ج',']':'چ',
'a':'ش','s':'س','d':'ی','f':'ب','g':'ل','h':'ا','j':'ت','k':'ن','l':'م',';':'ک',"'":'گ',
'z':'ظ','x':'ط','c':'ز','v':'ر','b':'ذ','n':'د','m':'پ',',':'و'
}

def en_keyboard_to_fa(text):
    result=""
    for ch in text:
        result+=EN_TO_FA.get(ch,ch)
    return result

def normalize_text(value):
    if pd.isna(value) or value is None:
        return ""
    text=str(value).strip().lower()
    text=text.replace("ي","ی").replace("ك","ک")
    text=text.replace("\u200c"," ")
    return " ".join(text.split())

@st.cache_data
def load_pricing_data():
    if not os.path.exists(PRICING_FILE):
        return pd.DataFrame(columns=["post_title","regular_price","clean_title"])
        
    df=pd.read_excel(
        PRICING_FILE,
        sheet_name=PRICING_SHEET,
        engine="openpyxl"
    )
    df=df[["post_title","regular_price"]].dropna(subset=["post_title"])
    df["post_title"]=df["post_title"].astype(str)
    df["clean_title"]=df["post_title"].map(normalize_text)
    return df

@st.cache_data
def load_exported_file():
    if not os.path.exists(EXPORTED_FOLDER):
        return pd.DataFrame(columns=["name","url","attribute","clean_name"])

    all_files=glob.glob(os.path.join(EXPORTED_FOLDER,"*.xlsx"))+\
               glob.glob(os.path.join(EXPORTED_FOLDER,"*.xls"))

    files=[f for f in all_files if not os.path.basename(f).startswith("~$")]

    if not files:
        return pd.DataFrame(columns=["name","url","attribute","clean_name"])

    exported_file=max(files,key=os.path.getmtime)
    df=pd.read_excel(exported_file,engine="openpyxl")
    first_col=df.columns[0]

    if "product_page_url" not in df.columns:
        df["product_page_url"]=""

    if "attribute:pa_tedaddarbasteh" not in df.columns:
        df["attribute:pa_tedaddarbasteh"]=""

    result=df[[first_col,"product_page_url","attribute:pa_tedaddarbasteh"]].copy()
    result.columns=["name","url","attribute"]
    result["name"]=result["name"].astype(str)
    result["clean_name"]=result["name"].map(normalize_text)

    return result

def format_price(value):
    try:
        value=int(float(value))
        return f"{value:,}"
    except:
        return value

# تنظیمات صفحه وب
st.set_page_config(page_title="Advanced Product Search", layout="wide")

st.markdown("<h1 style='text-align: right;'>جستجوی پیشرفته کالا</h1>", unsafe_allow_html=True)

# بارگذاری داده ها
data = load_pricing_data()
export_data = load_exported_file()

if data.empty:
    st.error(f"فایل اکسل پیدا نشد! لطفا فایل '{PRICING_FILE}' را در گیت‌هاب آپلود کنید.")

# نوار جستجو
search_query = st.text_input("جستجو:", placeholder="نام کالا را وارد کنید...")

if search_query:
    query_normal = normalize_text(search_query)
    query_keyboard = normalize_text(en_keyboard_to_fa(search_query))

    queries = [query_normal]
    if query_keyboard != query_normal:
        queries.append(query_keyboard)

    scored = []

    for _, row in data.iterrows():
        title = row["clean_title"]
        score = 0

        for q in queries:
            tokens = q.split()
            for token in tokens:
                if token in title:
                    score += 50
                else:
                    similarity = fuzz.partial_ratio(token, title)
                    if similarity > 70:
                        score += similarity / 2

        if score > 0:
            exported_match = export_data[
                export_data["clean_name"] == row["clean_title"]
            ]

            attribute_value = ""
            url_value = ""

            if not exported_match.empty:
                attribute_value = exported_match.iloc[0]["attribute"]
                url_value = exported_match.iloc[0]["url"]

            price = format_price(row["regular_price"])
            
            scored.append({
                "score": score,
                "تعداد در بسته": attribute_value,
                "قیمت": price,
                "نام کالا": row["post_title"],
                "لینک": url_value
            })

    # مرتب سازی بر اساس امتیاز
    scored.sort(key=lambda x: x["score"], reverse=True)
    results = scored[:150]

    if results:
        # ساخت دیتافریم برای نمایش
        df_results = pd.DataFrame(results)
        df_results = df_results.drop(columns=["score"])
        
        # نمایش نتایج به صورت جدول زیبا با قابلیت کلیک روی لینک ها
        st.dataframe(
            df_results,
            column_config={
                "لینک": st.column_config.LinkColumn(
                    "لینک صفحه محصول",
                    display_text="باز کردن در مرورگر"
                )
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.warning("کالایی یافت نشد!")
