import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io

st.set_page_config(
    page_title="نظام المطبعة الشامل والذكي (ERP - متكامل)",
    page_icon="🖨️",
    layout="wide"
)

DB_NAME = "printing_press_enterprise_v2.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Users Table
    cursor.execute(''' CREATE TABLE IF NOT EXISTS users ( user_id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, full_name TEXT NOT NULL, department TEXT NOT NULL, role TEXT NOT NULL, allowed_screens TEXT DEFAULT 'All' ) ''')
    
    # 2. Items & Inventory
    cursor.execute(''' CREATE TABLE IF NOT EXISTS items ( item_code TEXT PRIMARY KEY, item_name TEXT NOT NULL, category TEXT NOT NULL, unit TEXT NOT NULL, current_stock REAL DEFAULT 0, unit_price REAL DEFAULT 0 ) ''')
    
    # 3. Bill of Materials / Recipes (المواد الخام اللازمة لكل صنف نهائي)
    cursor.execute(''' CREATE TABLE IF NOT EXISTS item_recipes ( recipe_id INTEGER PRIMARY KEY AUTOINCREMENT, finished_item_code TEXT, raw_item_code TEXT, required_qty REAL NOT NULL, FOREIGN KEY(finished_item_code) REFERENCES items(item_code), FOREIGN KEY(raw_item_code) REFERENCES items(item_code) ) ''')
    
    # 4. Orders (الطلبيات)
    cursor.execute(''' CREATE TABLE IF NOT EXISTS orders ( order_id INTEGER PRIMARY KEY AUTOINCREMENT, order_date TEXT DEFAULT CURRENT_TIMESTAMP, customer_name TEXT NOT NULL, item_code TEXT, unit TEXT NOT NULL, quantity REAL NOT NULL, start_department TEXT NOT NULL, assigned_employee TEXT NOT NULL, execution_status TEXT DEFAULT 'غير منفذة', invoice_no TEXT, FOREIGN KEY(item_code) REFERENCES items(item_code) ) ''')
    
    # 5. Workflow Execution Tasks (سير العمل ومراحل الإنتاج)
    cursor.execute(''' CREATE TABLE IF NOT EXISTS workflow_tasks ( task_log_id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER, executing_dept TEXT NOT NULL, task_type TEXT NOT NULL, executing_employee TEXT NOT NULL, item_code TEXT NOT NULL, executed_quantity REAL NOT NULL, execution_date TEXT DEFAULT CURRENT_TIMESTAMP, execution_hours REAL DEFAULT 0, notes TEXT, FOREIGN KEY(order_id) REFERENCES orders(order_id), FOREIGN KEY(item_code) REFERENCES items(item_code) ) ''')
    
    # 6. Multi-Item Purchases (فواتير الشراء حتى 10+ اصناف)
    cursor.execute(''' CREATE TABLE IF NOT EXISTS purchase_invoices ( inv_id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_no TEXT UNIQUE NOT NULL, supplier_name TEXT NOT NULL, purchase_date TEXT DEFAULT CURRENT_TIMESTAMP, total_amount REAL DEFAULT 0 ) ''')
    cursor.execute(''' CREATE TABLE IF NOT EXISTS purchase_items ( p_item_id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_no TEXT NOT NULL, item_code TEXT NOT NULL, quantity REAL NOT NULL, unit_price REAL NOT NULL, total_price REAL NOT NULL, FOREIGN KEY(invoice_no) REFERENCES purchase_invoices(invoice_no), FOREIGN KEY(item_code) REFERENCES items(item_code) ) ''')
    
    # 7. Multi-Item Sales (فواتير البيع حتى 10+ اصناف)
    cursor.execute(''' CREATE TABLE IF NOT EXISTS sales_invoices ( s_inv_id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_no TEXT UNIQUE NOT NULL, order_id INTEGER, customer_name TEXT NOT NULL, sale_date TEXT DEFAULT CURRENT_TIMESTAMP, total_amount REAL DEFAULT 0, FOREIGN KEY(order_id) REFERENCES orders(order_id) ) ''')
    cursor.execute(''' CREATE TABLE IF NOT EXISTS sales_items ( s_item_id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_no TEXT NOT NULL, item_code TEXT NOT NULL, quantity REAL NOT NULL, unit_price REAL NOT NULL, total_price REAL NOT NULL, FOREIGN KEY(invoice_no) REFERENCES sales_invoices(invoice_no), FOREIGN KEY(item_code) REFERENCES items(item_code) ) ''')
    
    # 8. Accounting Module (الدليل المحاسبي والقيود المزدوجة وسندات القبض والصرف)
    cursor.execute(''' CREATE TABLE IF NOT EXISTS chart_of_accounts ( account_code TEXT PRIMARY KEY, account_name TEXT NOT NULL, account_type TEXT NOT NULL) ''')
    
    cursor.execute(''' CREATE TABLE IF NOT EXISTS journal_entries ( entry_id INTEGER PRIMARY KEY AUTOINCREMENT, entry_date TEXT DEFAULT CURRENT_TIMESTAMP, reference_no TEXT, description TEXT NOT NULL, account_code TEXT NOT NULL, debit REAL DEFAULT 0, credit REAL DEFAULT 0, FOREIGN KEY(account_code) REFERENCES chart_of_accounts(account_code) ) ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS vouchers (
        voucher_id INTEGER PRIMARY KEY AUTOINCREMENT,
        voucher_type TEXT NOT NULL,
        voucher_date TEXT DEFAULT CURRENT_TIMESTAMP,
        beneficiary TEXT NOT NULL,
        amount REAL NOT NULL,
        account_code TEXT NOT NULL,
        description TEXT,
        FOREIGN KEY(account_code) REFERENCES chart_of_accounts(account_code)
    )
''')
    
    # Seed default accounts if empty
    cursor.execute("SELECT COUNT(*) FROM chart_of_accounts")
    if cursor.fetchone()[0] == 0:
        default_accounts = [
            ("101", "الصندوق الرئيسي", "أصول"),
            ("102", "البنك", "أصول"),
            ("103", "مخزون المواد الخام", "أصول"),
            ("104", "مخزون الإنتاج التام", "أصول"),
            ("201", "الموردين", "خصوم"),
            ("301", "رأس المال", "حقوق ملكية"),
            ("401", "إيرادات المبيعات", "إيرادات"),
            ("501", "مصروفات أجور العمال", "مصروفات"),
            ("502", "مصروفات التشغيل", "مصروفات")
        ]
        cursor.executemany("INSERT INTO chart_of_accounts VALUES (?, ?, ?)", default_accounts)
        
    # Seed default admin user if empty
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (username, password, full_name, department, role, allowed_screens) VALUES ('admin', '1234', 'مدير النظام العام', 'الإدارة العليا', 'Admin', 'All')")
        
    conn.commit()
    conn.close()

init_db()

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.session_state["full_name"] = ""
    st.session_state["role"] = ""
    st.session_state["allowed_screens"] = "All"

# --- LOGIN SCREEN ---
if not st.session_state["logged_in"]:
    st.markdown("<h1 style='text-align: center; color: #1F4E78;'>🖨️ نظام المطبعة الشامل والذكي (ERP - متكامل)</h1>", unsafe_allow_html=True)
    st.markdown("<h4 style='text-align: center; color: gray;'>تسجيل الدخول الموحد</h4>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("اسم المستخدم")
            password = st.text_input("كلمة المرور", type="password")
            submit = st.form_submit_button("تسجيل الدخول", use_container_width=True)
            
            if submit:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT full_name, role, department, allowed_screens FROM users WHERE username = ? AND password = ?", (username, password))
                user = cursor.fetchone()
                conn.close()
                
                if user:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = username
                    st.session_state["full_name"] = user[0]
                    st.session_state["role"] = user[1]
                    st.session_state["allowed_screens"] = user[3]
                    st.success("تم تسجيل الدخول بنجاح!")
                    st.rerun()
                else:
                    st.error("اسم المستخدم أو كلمة المرور غير صحيحة!")
                    
        st.info("💡 **حساب الأدمن الافتراضي:** `admin` / كلمة المرور: `1234`")
    st.stop()

# --- SIDEBAR MENU ---
role = st.session_state["role"]
full_name = st.session_state["full_name"]
allowed = st.session_state["allowed_screens"]

st.sidebar.title(f"👤 {full_name}")
st.sidebar.markdown(f"**الصلاحية:** `{role}`")
st.sidebar.markdown("---")

all_menu_options = {
    "📊 لوحة المؤشرات والاختصارات": "Dashboard",
    "📦 إدارة المخزون والأصناف والتقارير": "Inventory",
    "🧪 وصفات التصنيع وصرف المواد": "Production_Recipe",
    "📥 فواتير الشراء (10+ اصناف)": "Purchases",
    "💰 فواتير البيع (10+ اصناف)": "Sales",
    "📋 إدارة الطلبيات وسير العمل": "Orders_Workflow",
    "📈 تقارير أعمال العمال التفصيلية": "Workers_Reports",
    "📑 الدليل المحاسبي والقيود والسندات": "Accounting",
    "🔐 إعدادات الحساب وكلمة المرور": "Password",
    "🛠️ إدارة المستخدمين والصلاحيات": "Admin_Users"
}

available_menus = []
for title, key in all_menu_options.items():
    if role == "Admin" or allowed == "All" or key in allowed.split(","):
        available_menus.append(title)

menu = st.sidebar.radio("القائمة الرئيسية", available_menus)

if st.sidebar.button("🚪 تسجيل الخروج", use_container_width=True):
    st.session_state["logged_in"] = False
    st.rerun()

conn = get_connection()

# ================= 1. DASHBOARD & SHORTCUTS =================
if menu == "📊 لوحة المؤشرات والاختصارات":
    st.title("📊 لوحة المؤشرات والتحكم الرئيسية (اختصارات النظام)")
    st.markdown("---")
    
    total_orders = pd.read_sql("SELECT COUNT(*) FROM orders", conn).iloc[0, 0]
    unexecuted_orders = pd.read_sql("SELECT COUNT(*) FROM orders WHERE execution_status = 'غير منفذة'", conn).iloc[0, 0]
    total_items = pd.read_sql("SELECT COUNT(*) FROM items", conn).iloc[0, 0]
    total_sales = pd.read_sql("SELECT SUM(total_amount) FROM sales_invoices", conn).iloc[0, 0] or 0.0
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("إجمالي الطلبيات", total_orders)
    col2.metric("الطلبيات غير المنفذة", unexecuted_orders)
    col3.metric("عدد الأصناف", total_items)
    col4.metric("إجمالي المبيعات", f"{total_sales:,.2f} ر.ي")
    
    st.markdown("### ⚡ اختصارات سريعة للعمليات الهامة")
    sc1, sc2, sc3, sc4 = st.columns(4)
    with sc1:
        if st.button("📦 إضافة صنف جديد", use_container_width=True):
            st.rerun()
    with sc2:
        if st.button("📥 فاتورة شراء جديدة", use_container_width=True):
            st.rerun()
    with sc3:
        if st.button("📋 تسجيل طلبيّة جديدة", use_container_width=True):
            st.rerun()
    with sc4:
        if st.button("📑 سند صرف / قبض", use_container_width=True):
            st.rerun()
            
    st.markdown("### 🚀 ملخص حركة العمل والطلبيات الحديثة")
    df_o = pd.read_sql("SELECT order_id AS 'رقم الطلبية', customer_name AS 'العميل', quantity AS 'الكمية', start_department AS 'قسم البداية', execution_status AS 'الحالة' FROM orders", conn)
    st.dataframe(df_o, use_container_width=True)

# ================= 2. INVENTORY & PRINT REPORT =================
elif menu == "📦 إدارة المخزون والأصناف والتقارير":
    st.title("📦 إدارة الأصناف والمخزون وتقارير الرصيد الشاملة")
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["قائمة الأصناف وحركة الوارد والمنصرف", "إضافة صنف جديد / تعديل", "طباعة تقرير المخزون الشامل"])
    
    with tab1:
        df_items = pd.read_sql("SELECT item_code AS 'كود الصنف', item_name AS 'اسم الصنف', category AS 'التصنيف', unit AS 'الوحدة', current_stock AS 'الرصيد الحالي', unit_price AS 'سعر الوحدة (ر.ي)' FROM items", conn)
        st.dataframe(df_items, use_container_width=True)
        
        st.markdown("### 📊 تقرير حركة الوارد والمنصرف لكل صنف")
        if not df_items.empty:
            sel_rep = st.selectbox("اختر الصنف لعرض حركته", options=df_items['كود الصنف'].tolist(), format_func=lambda x: df_items.loc[df_items['كود الصنف'] == x, 'اسم الصنف'].values[0])
            
            st.markdown("#### الوارد (مشتريات)")
            df_p = pd.read_sql(f"SELECT invoice_no AS 'رقم الفاتورة', supplier_name AS 'المورد', quantity AS 'الكمية الواردة', unit_price AS 'السعر', purchase_date AS 'التاريخ' FROM purchase_invoices pi JOIN purchase_items pit ON pi.invoice_no = pit.invoice_no WHERE pit.item_code = '{sel_rep}'", conn)
            st.dataframe(df_p, use_container_width=True)
            
            st.markdown("#### المنصرف (مبيعات)")
            df_s = pd.read_sql(f"SELECT invoice_no AS 'رقم الفاتورة', customer_name AS 'العميل', quantity AS 'الكمية المباعة', unit_price AS 'السعر', sale_date AS 'التاريخ' FROM sales_invoices si JOIN sales_items sit ON si.invoice_no = sit.invoice_no WHERE sit.item_code = '{sel_rep}'", conn)
            st.dataframe(df_s, use_container_width=True)

    with tab2:
        with st.form("add_item_form"):
            c1, c2 = st.columns(2)
            with c1:
                icode = st.text_input("كود الصنف (مثال: RM-01)")
                iname = st.text_input("اسم الصنف")
                cat = st.selectbox("التصنيف", ["مادة خام", "منتج نهائي"])
            with c2:
                unit = st.text_input("الوحدة (رزمة، قطعة، لتر، دفتر)")
                stock = st.number_input("الرصيد الابتدائي", min_value=0.0, value=0.0)
                price = st.number_input("سعر الوحدة (ر.ي)", min_value=0.0, value=0.0)
                
            if st.form_submit_button("حفظ الصنف في النظام"):
                try:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO items VALUES (?, ?, ?, ?, ?, ?)", (icode, iname, cat, unit, stock, price))
                    conn.commit()
                    st.success("تم حفظ الصنف بنجاح!")
                    st.rerun()
                except Exception as e:
                    st.error(f"خطأ: كود الصنف موجود مسبقاً ({e})")

    with tab3:
        st.subheader("🖨️ تقرير طباعة أرصدة وقيمة المخزون التفصيلي")
        df_inv_full = pd.read_sql("SELECT item_code AS 'كود الصنف', item_name AS 'اسم الصنف', category AS 'التصنيف', unit AS 'الوحدة', current_stock AS 'الرصيد المتبقي', unit_price AS 'السعر', (current_stock * unit_price) AS 'إجمالي القيمة (ر.ي)' FROM items", conn)
        st.dataframe(df_inv_full, use_container_width=True)
        
        total_inv_val = df_inv_full['إجمالي القيمة (ر.ي)'].sum() if not df_inv_full.empty else 0.0
        st.markdown(f"### 💰 إجمالي قيمة المخزون العام: `{total_inv_val:,.2f} ر.ي`")
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_inv_full.to_excel(writer, sheet_name='تقرير المخزون', index=False)
        output.seek(0)
        st.download_button("📥 تنزيل تقرير المخزون إكسل (.xlsx)", data=output, file_name="Inventory_Report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ================= 3. PRODUCTION RECIPES & MATERIAL CONSUMPTION =================
elif menu == "🧪 وصفات التصنيع وصرف المواد":
    st.title("🧪 ربط المنتجات النهائية بالمواد الخام وإثبات الإنتاج")
    st.markdown("---")
    
    tab_r1, tab_r2 = st.tabs(["تحديد المواد الخام لكل صنف نهائي (Recipe)", "إثبات الإنتاج وخصم المواد الخام"])
    
    with tab_r1:
        with st.form("recipe_form"):
            finished_items = pd.read_sql("SELECT item_code, item_name FROM items WHERE category = 'منتج نهائي'", conn)
            raw_items = pd.read_sql("SELECT item_code, item_name FROM items WHERE category = 'مادة خام'", conn)
            
            f_code = st.selectbox("المنتج النهائي", options=finished_items['item_code'].tolist(), format_func=lambda x: finished_items.loc[finished_items['item_code'] == x, 'item_name'].values[0]) if not finished_items.empty else None
            r_code = st.selectbox("المادة الخام المستخدمة", options=raw_items['item_code'].tolist(), format_func=lambda x: raw_items.loc[raw_items['item_code'] == x, 'item_name'].values[0]) if not raw_items.empty else None
            req_qty = st.number_input("الكمية المطلوبة من المادة الخام لكل وحدة منتج", min_value=0.001, value=1.0)
            
            if st.form_submit_button("حفظ الوصفة"):
                if f_code and r_code:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO item_recipes (finished_item_code, raw_item_code, required_qty) VALUES (?, ?, ?)", (f_code, r_code, req_qty))
                    conn.commit()
                    st.success("تم حفظ وصفة التصنيع بنجاح!")
                    st.rerun()
                    
        st.markdown("### قائمة الوصفات المسجلة")
        df_rec = pd.read_sql(""" SELECT r.recipe_id AS 'معرف', f.item_name AS 'المنتج النهائي', rw.item_name AS 'المادة الخام', r.required_qty AS 'الكمية اللازمة' FROM item_recipes r JOIN items f ON r.finished_item_code = f.item_code JOIN items rw ON r.raw_item_code = rw.item_code """, conn)
        st.dataframe(df_rec, use_container_width=True)

    with tab_r2:
        with st.form("produce_form"):
            st.subheader("شاشة إثبات كمية الإنتاج التام وخصم المواد الخام تلقائياً")
            finished_items2 = pd.read_sql("SELECT item_code, item_name FROM items WHERE category = 'منتج نهائي'", conn)
            prod_item = st.selectbox("المنتج النهائي المراد إنتاجه", options=finished_items2['item_code'].tolist(), format_func=lambda x: finished_items2.loc[finished_items2['item_code'] == x, 'item_name'].values[0]) if not finished_items2.empty else None
            prod_qty = st.number_input("الكمية المنتجة (التاّمة)", min_value=1.0, value=100.0)
            
            if st.form_submit_button("تأكيد الإنتاج وخصم المواد الخام"):
                if prod_item:
                    cursor = conn.cursor()
                    # Get recipe materials
                    recipes = pd.read_sql(f"SELECT raw_item_code, required_qty FROM item_recipes WHERE finished_item_code = '{prod_item}'", conn)
                    if recipes.empty:
                        st.error("لا توجد وصفة مسجلة لهذا المنتج النهائي! يرجى إضافتها أولاً.")
                    else:
                        # Deduct raw materials and add finished goods
                        success = True
                        for _, row in recipes.iterrows():
                            raw_c = row['raw_item_code']
                            needed = row['required_qty'] * prod_qty
                            # check stock
                            stk = pd.read_sql(f"SELECT current_stock FROM items WHERE item_code = '{raw_c}'", conn).iloc[0, 0]
                            if stk < needed:
                                success = False
                                st.error(f"رصيد المادة الخام ({raw_c}) غير كافٍ في المخزن! المطلوبة: {needed}, المتوفر: {stk}")
                                break
                        
                        if success:
                            for _, row in recipes.iterrows():
                                raw_c = row['raw_item_code']
                                needed = row['required_qty'] * prod_qty
                                cursor.execute("UPDATE items SET current_stock = current_stock - ? WHERE item_code = ?", (needed, raw_c))
                            
                            cursor.execute("UPDATE items SET current_stock = current_stock + ? WHERE item_code = ?", (prod_qty, prod_item))
                            conn.commit()
                            st.success(f"تم إثبات إنتاج {prod_qty} وحدة من المنتج النهائي وخصم المواد الخام من المخزون بنجاح!")
                            st.rerun()

# ================= 4. MULTI-ITEM PURCHASES (10+ ITEMS) =================
elif menu == "📥 فواتير الشراء (10+ اصناف)":
    st.title("📥 فواتير الشراء متعددة الأصناف (تدعم أكثر من 10 أصناف)")
    st.markdown("---")
    
    with st.form("purchases_10_form"):
        st.subheader("رأس الفاتورة")
        p_inv = st.text_input("رقم فاتورة الشراء")
        p_supp = st.text_input("اسم المورد")
        
        st.subheader("بنود الأصناف (حتى 15 صنفاً)")
        all_raw = pd.read_sql("SELECT item_code, item_name FROM items WHERE category = 'مادة خام'", conn)
        
        if all_raw.empty:
            st.warning("يرجى إضافة مواد خام أولاً.")
        else:
            items_data = []
            total_inv_calc = 0
            for i in range(1, 16):
                col_p1, col_p2, col_p3 = st.columns(3)
                with col_p1:
                    it = st.selectbox(f"الصنف {i}", options=["لا يوجد"] + all_raw['item_code'].tolist(), format_func=lambda x: "لا يوجد" if x=="لا يوجد" else all_raw.loc[all_raw['item_code'] == x, 'item_name'].values[0], key=f"p_it_{i}")
                with col_p2:
                    qt = st.number_input(f"الكمية {i}", min_value=0.0, value=0.0, key=f"p_qt_{i}")
                with col_p3:
                    pr = st.number_input(f"السعر {i}", min_value=0.0, value=0.0, key=f"p_pr_{i}")
                
                if it != "لا يوجد" and qt > 0:
                    items_data.append((it, qt, pr, qt * pr))
            
            if st.form_submit_button("حفظ فاتورة الشراء وتحديث المخزن"):
                if p_inv and p_supp and items_data:
                    try:
                        cursor = conn.cursor()
                        tot_amt = sum([x[3] for x in items_data])
                        cursor.execute("INSERT INTO purchase_invoices (invoice_no, supplier_name, total_amount) VALUES (?, ?, ?)", (p_inv, p_supp, tot_amt))
                        for itm in items_data:
                            cursor.execute("INSERT INTO purchase_items (invoice_no, item_code, quantity, unit_price, total_price) VALUES (?, ?, ?, ?, ?)", (p_inv, itm[0], itm[1], itm[2], itm[3]))
                            cursor.execute("UPDATE items SET current_stock = current_stock + ? WHERE item_code = ?", (itm[1], itm[0]))
                        conn.commit()
                        st.success("تم حفظ فاتورة الشراء وتحديث المخازن بنجاح!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"خطأ: رقم الفاتورة موجود مسبقاً ({e})")
                else:
                    st.warning("يرجى إدخال رقم الفاتورة، اسم المورد، وصنف واحد على الأقل.")

    st.markdown("### سجل فواتير الشراء")
    df_p_all = pd.read_sql("SELECT invoice_no AS 'رقم الفاتورة', supplier_name AS 'المورد', total_amount AS 'إجمالي الفاتورة (ر.ي)', purchase_date AS 'التاريخ' FROM purchase_invoices", conn)
    st.dataframe(df_p_all, use_container_width=True)

# ================= 5. MULTI-ITEM SALES (10+ ITEMS) =================
elif menu == "💰 فواتير البيع (10+ اصناف)":
    st.title("💰 فواتير البيع متعددة الأصناف (تدعم أكثر من 10 أصناف)")
    st.markdown("---")
    
    with st.form("sales_10_form"):
        st.subheader("رأس فاتورة البيع")
        s_inv = st.text_input("رقم فاتورة البيع")
        s_cust = st.text_input("اسم العميل")
        
        st.subheader("بنود الأصناف المباعة (حتى 15 صنفاً)")
        all_items_sale = pd.read_sql("SELECT item_code, item_name FROM items", conn)
        
        if all_items_sale.empty:
            st.warning("لا توجد أصناف مسجلة.")
        else:
            s_items_data = []
            for i in range(1, 16):
                col_s1, col_s2, col_s3 = st.columns(3)
                with col_s1:
                    sit = st.selectbox(f"الصنف المباع {i}", options=["لا يوجد"] + all_items_sale['item_code'].tolist(), format_func=lambda x: "لا يوجد" if x=="لا يوجد" else all_items_sale.loc[all_items_sale['item_code'] == x, 'item_name'].values[0], key=f"s_it_{i}")
                with col_s2:
                    sqt = st.number_input(f"الكمية المباعة {i}", min_value=0.0, value=0.0, key=f"s_qt_{i}")
                with col_s3:
                    spr = st.number_input(f"سعر البيع {i}", min_value=0.0, value=0.0, key=f"s_pr_{i}")
                
                if sit != "لا يوجد" and sqt > 0:
                    s_items_data.append((sit, sqt, spr, sqt * spr))
            
            if st.form_submit_button("إصدار فاتورة البيع وتحديث المخزن"):
                if s_inv and s_cust and s_items_data:
                    try:
                        cursor = conn.cursor()
                        tot_s_amt = sum([x[3] for x in s_items_data])
                        cursor.execute("INSERT INTO sales_invoices (invoice_no, customer_name, total_amount) VALUES (?, ?, ?)", (s_inv, s_cust, tot_s_amt))
                        for sitm in s_items_data:
                            cursor.execute("INSERT INTO sales_items (invoice_no, item_code, quantity, unit_price, total_price) VALUES (?, ?, ?, ?, ?)", (s_inv, sitm[0], sitm[1], sitm[2], sitm[3]))
                            cursor.execute("UPDATE items SET current_stock = current_stock - ? WHERE item_code = ?", (sitm[1], sitm[0]))
                        conn.commit()
                        st.success("تم إصدار فاتورة البيع وخصم الكميات من المخزن بنجاح!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"خطأ: رقم الفاتورة موجود مسبقاً ({e})")
                else:
                    st.warning("يرجى إدخال رقم الفاتورة، اسم العميل، وصنف واحد على الأقل.")

    st.markdown("### سجل فواتير المبيعات")
    df_s_all = pd.read_sql("SELECT invoice_no AS 'رقم الفاتورة', customer_name AS 'العميل', total_amount AS 'إجمالي الفاتورة (ر.ي)', sale_date AS 'التاريخ' FROM sales_invoices", conn)
    st.dataframe(df_s_all, use_container_width=True)

# ================= 6. ORDERS & WORKFLOW (SPLIT INTO 2 TABS) =================
elif menu == "📋 إدارة الطلبيات وسير العمل":
    st.title("📋 إدارة الطلبيات وسير العمل ومراحل الإنتاج")
    st.markdown("---")
    
    tab_ow1, tab_ow2 = st.tabs(["1. الطلبيات (Orders)", "2. سير العمل ومراحل الإنتاج (Workflow)"])
    
    with tab_ow1:
        st.subheader("تسجيل ومتابعة الطلبيات الجديدة")
        with st.form("new_order_split_form"):
            c_name = st.text_input("اسم العميل")
            all_fin = pd.read_sql("SELECT item_code, item_name FROM items", conn)
            ord_item = st.selectbox("اسم الصنف", options=all_fin['item_code'].tolist(), format_func=lambda x: all_fin.loc[all_fin['item_code'] == x, 'item_name'].values[0]) if not all_fin.empty else None
            ord_unit = st.text_input("الوحدة (قطعة، دفتر، رزمة)", value="قطعة")
            ord_qty = st.number_input("الكمية", min_value=1.0, value=100.0)
            start_dept = st.selectbox("القسم الذي سيبدأ بالتنفيذ", ["قسم الطباعة", "قسم الفرز والتدبيس", "قسم التغرية والتعريش", "قسم البنر وسلك سكرين"])
            emp_name = st.text_input("اسم الموظف المسؤول عن الطلبية")
            
            if st.form_submit_button("حفظ الطلبية في النظام"):
                if ord_item and c_name:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO orders (customer_name, item_code, unit, quantity, start_department, assigned_employee, execution_status) VALUES (?, ?, ?, ?, ?, ?, 'غير منفذة')", (c_name, ord_item, ord_unit, ord_qty, start_dept, emp_name))
                    conn.commit()
                    st.success("تم تسجيل الطلبية بنجاح!")
                    st.rerun()
                    
        st.markdown("### 📋 تقرير الطلبيات غير المنفذة")
        df_unexec = pd.read_sql(""" SELECT o.order_id AS 'رقم الطلبية', o.customer_name AS 'العميل', i.item_name AS 'الصنف', o.unit AS 'الوحدة', o.quantity AS 'الكمية', o.start_department AS 'قسم البداية', o.assigned_employee AS 'الموظف المسؤول' FROM orders o JOIN items i ON o.item_code = i.item_code WHERE o.execution_status = 'غير منفذة' """, conn)
        st.dataframe(df_unexec, use_container_width=True)

    with tab_ow2:
        st.subheader("متابعة سير العمل ومراحل الإنتاج وتفاصيل التنفيذ")
        active_ords = pd.read_sql("SELECT order_id, customer_name FROM orders", conn)
        
        with st.form("workflow_task_form"):
            sel_ord_id = st.selectbox("رقم الطلبية", options=active_ords['order_id'].tolist(), format_func=lambda x: f"طلبية #{x} - {active_ords.loc[active_ords['order_id'] == x, 'customer_name'].values[0]}") if not active_ords.empty else None
            exec_dept = st.selectbox("القسم المنفذ", ["قسم الطباعة", "قسم الفرز والتدبيس", "قسم التغرية والتعريش", "قسم البنر وسلك سكرين"])
            task_type = st.selectbox("نوع المهمة المنفذة", ["طباعة", "فرز", "تدبيس", "تعريش", "ربط", "كبس", "تغليف"])
            exec_emp = st.text_input("الموظف المنفذ")
            wf_item = st.selectbox("اسم الصنف المنفذ", options=all_fin['item_code'].tolist(), format_func=lambda x: all_fin.loc[all_fin['item_code'] == x, 'item_name'].values[0]) if not all_fin.empty else None
            exec_qty = st.number_input("الكمية المنفذة", min_value=1.0, value=100.0)
            exec_hours = st.number_input("عدد ساعات التنفيذ", min_value=0.1, value=2.0)
            wf_notes = st.text_area("ملاحظات إضافية")
            
            if st.form_submit_button("💾 حفظ المهام المدخلة إلى النظام"):
                if sel_ord_id and wf_item:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO workflow_tasks (order_id, executing_dept, task_type, executing_employee, item_code, executed_quantity, execution_hours, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (sel_ord_id, exec_dept, task_type, exec_emp, wf_item, exec_qty, exec_hours, wf_notes))
                    cursor.execute("UPDATE orders SET execution_status = 'منفذة جزئياً' WHERE order_id = ?", (sel_ord_id,))
                    conn.commit()
                    st.success("تم حفظ مهمة سير العمل وتحديث حالة الطلبية بنجاح!")
                    st.rerun()
                    
        st.markdown("### سجل مهام سير العمل المسجلة")
        df_wf_log = pd.read_sql(""" SELECT w.task_log_id AS 'معرف', w.order_id AS 'رقم الطلبية', w.executing_dept AS 'القسم', w.task_type AS 'نوع المهمة', w.executing_employee AS 'الموظف', i.item_name AS 'الصنف', w.executed_quantity AS 'الكمية المنفذة', w.execution_hours AS 'الساعات', w.execution_date AS 'التاريخ' FROM workflow_tasks w JOIN items i ON w.item_code = i.item_code """, conn)
        st.dataframe(df_wf_log, use_container_width=True)

# ================= 7. DETAILED WORKER & TASK REPORTS =================
elif menu == "📈 تقارير أعمال العمال التفصيلية":
    st.title("📈 تقارير أعمال العمال وسير العمل التفصيلية")
    st.markdown("---")
    
    st.markdown("### فلترة واستخراج التقارير")
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        rep_emp = st.text_input("بحث باسم الموظف (اتركه فارغاً للجميع)")
    with col_r2:
        rep_task = st.selectbox("نوع العمل", ["الكل", "طباعة", "فرز", "تدبيس", "تعريش", "ربط", "كبس", "تغليف"])
        
    query_rep = """ SELECT w.task_log_id AS 'معرف', w.order_id AS 'الطلبية', w.executing_dept AS 'القسم', w.task_type AS 'نوع العمل', w.executing_employee AS 'الموظف', i.item_name AS 'الصنف', w.executed_quantity AS 'الكمية', w.execution_hours AS 'الساعات', w.execution_date AS 'التاريخ' FROM workflow_tasks w JOIN items i ON w.item_code = i.item_code WHERE 1=1 """
    if rep_emp:
        query_rep += f" AND w.executing_employee LIKE '%{rep_emp}%'"
    if rep_task != "الكل":
        query_rep += f" AND w.task_type = '{rep_task}'"
        
    df_report = pd.read_sql(query_rep, conn)
    st.dataframe(df_report, use_container_width=True)
    
    # Export options
    if not df_report.empty:
        col_ex1, col_ex2 = st.columns(2)
        with col_ex1:
            out_ex = io.BytesIO()
            with pd.ExcelWriter(out_ex, engine='openpyxl') as writer:
                df_report.to_excel(writer, sheet_name='تقرير العمال', index=False)
            out_ex.seek(0)
            st.download_button("📥 تصدير التقرير إكسل (.xlsx)", data=out_ex, file_name="Worker_Detailed_Report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        with col_ex2:
            csv_data = df_report.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 تصدير التقرير CSV/Word", data=csv_data, file_name="Worker_Detailed_Report.csv", mime="text/csv")

# ================= 8. ACCOUNTING MODULE =================
elif menu == "📑 الدليل المحاسبي والقيود والسندات":
    st.title("📑 الدليل المحاسبي، القيود المزدوجة، والسندات المالية")
    st.markdown("---")
    
    t_acc1, t_acc2, t_acc3, t_acc4 = st.tabs(["الدليل المحاسبي", "قيود اليومية المزدوجة", "سندات القبض والصرف", "ميزان المراجعة والحسابات الختامية"])
    
    with t_acc1:
        df_acc = pd.read_sql("SELECT account_code AS 'رقم الحساب', account_name AS 'اسم الحساب', account_type AS 'طبيعة الحساب' FROM chart_of_accounts", conn)
        st.dataframe(df_acc, use_container_width=True)
        
        with st.form("new_acc_form"):
            st.subheader("إضافة حساب جديد للدليل المحاسبي")
            ac_code = st.text_input("رقم الحساب (مثال: 105)")
            ac_name = st.text_input("اسم الحساب")
            ac_type = st.selectbox("طبيعة الحساب", ["أصول", "خصوم", "إيرادات", "مصروفات", "حقوق ملكية"])
            if st.form_submit_button("إضافة الحساب"):
                try:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO chart_of_accounts VALUES (?, ?, ?)", (ac_code, ac_name, ac_type))
                    conn.commit()
                    st.success("تمت إضافة الحساب بنجاح!")
                    st.rerun()
                except Exception as e:
                    st.error(f"خطأ: الحساب موجود مسبقاً ({e})")

    with t_acc2:
        with st.form("journal_entry_form"):
            st.subheader("إثبات قيد يومي مزدوج (مدين / دائن)")
            j_desc = st.text_input("بيان القيد / وصف العملية")
            accounts_list = pd.read_sql("SELECT account_code, account_name FROM chart_of_accounts", conn)
            
            ac_deb = st.selectbox("الحساب المدين", options=accounts_list['account_code'].tolist(), format_func=lambda x: accounts_list.loc[accounts_list['account_code'] == x, 'account_name'].values[0])
            deb_amt = st.number_input("مبلغ المدين (ر.ي)", min_value=0.0, value=1000.0)
            
            ac_cred = st.selectbox("الحساب الدائن", options=accounts_list['account_code'].tolist(), format_func=lambda x: accounts_list.loc[accounts_list['account_code'] == x, 'account_name'].values[0])
            cred_amt = st.number_input("مبلغ الدائن (ر.ي)", min_value=0.0, value=1000.0)
            
            if st.form_submit_button("ترحيل القيد المزدوج"):
                if deb_amt == cred_amt and deb_amt > 0:
                    cursor = conn.cursor()
                    # Insert debit entry
                    cursor.execute("INSERT INTO journal_entries (description, account_code, debit, credit) VALUES (?, ?, ?, 0)", (j_desc, ac_deb, deb_amt))
                    # Insert credit entry
                    cursor.execute("INSERT INTO journal_entries (description, account_code, debit, credit) VALUES (?, ?, 0, ?)", (j_desc, ac_cred, cred_amt))
                    conn.commit()
                    st.success("تم ترحيل القيد المحاسبي بنجاح!")
                    st.rerun()
                else:
                    st.error("خطأ: يجب أن يتساوى الطرف المدين مع الطرف الدائن وأن يكون المبلغ أكبر من صفر.")
                    
        st.markdown("### سجل قيود اليومية المحاسبية")
        df_j = pd.read_sql("SELECT entry_id AS 'معرف', entry_date AS 'التاريخ', description AS 'البيان', account_code AS 'رقم الحساب', debit AS 'مدين (ر.ي)', credit AS 'دائن (ر.ي)' FROM journal_entries", conn)
        st.dataframe(df_j, use_container_width=True)

    with t_acc3:
        with st.form("voucher_financial_form"):
            st.subheader("إصدار سند قبض أو سند صرف يومي")
            v_type = st.selectbox("نوع السند", ["سند قبض", "سند صرف"])
            v_benef = st.text_input("اسم المستفيد / الجهة الدافع")
            v_amt = st.number_input("المبلغ (ر.ي)", min_value=0.1, value=5000.0)
            accounts_list2 = pd.read_sql("SELECT account_code, account_name FROM chart_of_accounts", conn)
            v_acc = st.selectbox("الحساب المقابل", options=accounts_list2['account_code'].tolist(), format_func=lambda x: accounts_list2.loc[accounts_list2['account_code'] == x, 'account_name'].values[0])
            v_desc = st.text_input("البيان والسبب")
            
            if st.form_submit_button("حفظ وترحيل السند"):
                cursor = conn.cursor()
                cursor.execute("INSERT INTO vouchers (voucher_type, beneficiary, amount, account_code, description) VALUES (?, ?, ?, ?, ?)", (v_type, v_benef, v_amt, v_acc, v_desc))
                conn.commit()
                st.success("تم حفظ السند المالي بنجاح!")
                st.rerun()
                
        st.markdown("### سجل السندات المالية")
        df_v = pd.read_sql("SELECT voucher_id AS 'معرف', voucher_type AS 'نوع السند', beneficiary AS 'المستفيد', amount AS 'المبلغ (ر.ي)', description AS 'البيان', voucher_date AS 'التاريخ' FROM vouchers", conn)
        st.dataframe(df_v, use_container_width=True)

    with t_acc4:
        st.subheader("⚖️ ميزان المراجعة والحسابات الختامية")
        df_tb = pd.read_sql(""" SELECT c.account_code AS 'رقم الحساب', c.account_name AS 'اسم الحساب', c.account_type AS 'النوع', COALESCE(SUM(j.debit), 0) AS 'إجمالي المدين', COALESCE(SUM(j.credit), 0) AS 'إجمالي الدائن' FROM chart_of_accounts c LEFT JOIN journal_entries j ON c.account_code = j.account_code GROUP BY c.account_code, c.account_name, c.account_type """, conn)
        st.dataframe(df_tb, use_container_width=True)
        
        tot_deb = df_tb['إجمالي المدين'].sum()
        tot_cred = df_tb['إجمالي الدائن'].sum()
        st.markdown(f"### إجمالي الميزان: المدين (`{tot_deb:,.2f}`) | الدائن (`{tot_cred:,.2f}`)")

# ================= 9. PASSWORD CHANGE =================
elif menu == "🔐 إعدادات الحساب وكلمة المرور":
    st.title("🔐 تغيير كلمة المرور الخاصة بحسابك")
    st.markdown("---")
    
    with st.form("change_pass_form"):
        old_p = st.text_input("كلمة المرور الحالية", type="password")
        new_p = st.text_input("كلمة المرور الجديدة", type="password")
        conf_p = st.text_input("تأكيد كلمة المرور الجديدة", type="password")
        
        if st.form_submit_button("تحديث كلمة المرور"):
            conn_u = get_connection()
            cur_u = conn_u.cursor()
            cur_u.execute("SELECT password FROM users WHERE username = ?", (st.session_state["username"],))
            db_pass = cur_u.fetchone()[0]
            
            if old_p == db_pass:
                if new_p == conf_p and new_p != "":
                    cur_u.execute("UPDATE users SET password = ? WHERE username = ?", (new_p, st.session_state["username"]))
                    conn_u.commit()
                    conn_u.close()
                    st.success("تم تغيير كلمة المرور بنجاح!")
                else:
                    st.error("كلمة المرور الجديدة غير متطابقة أو فارغة.")
            else:
                st.error("كلمة المرور الحالية غير صحيحة.")
            conn_u.close()

# ================= 10. ADMIN USERS & PERMISSIONS =================
elif menu == "🛠️ إدارة المستخدمين والصلاحيات":
    if role != "Admin":
        st.error("عذراً، هذه الصفحة مخصصة لمدير النظام (Admin) فقط.")
    else:
        st.title("🛠️ إدارة المستخدمين والصلاحيات الشاملة")
        st.markdown("---")
        
        with st.form("add_user_full"):
            st.subheader("إضافة مستخدم جديد وتحديد دوره وأنواع المهام")
            u_name = st.text_input("اسم المستخدم")
            u_pass = st.text_input("كلمة المرور")
            u_full = st.text_input("الاسم الكامل للعامل")
            u_dept = st.text_input("القسم")
            u_role = st.selectbox("الدور", ["Admin", "Worker"])
            
            if st.form_submit_button("إضافة المستخدم"):
                try:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO users (username, password, full_name, department, role, allowed_screens) VALUES (?, ?, ?, ?, ?, 'All')", (u_name, u_pass, u_full, u_dept, u_role))
                    conn.commit()
                    st.success("تم إضافة المستخدم بنجاح!")
                    st.rerun()
                except Exception as e:
                    st.error(f"خطأ: اسم المستخدم موجود مسبقاً ({e})")
                    
        st.markdown("### قائمة المستخدمين الحاليين")
        df_usr = pd.read_sql("SELECT username AS 'اسم المستخدم', full_name AS 'الاسم الكامل', department AS 'القسم', role AS 'الصلاحية' FROM users", conn)
        st.dataframe(df_usr, use_container_width=True)

conn.close()
