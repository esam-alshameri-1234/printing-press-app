import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="نظام المطبعة الشامل والذكي",
    page_icon="🖨️",
    layout="wide"
)

DB_NAME = "printing_press_pro.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            department TEXT NOT NULL,
            role TEXT NOT NULL,
            allowed_screens TEXT DEFAULT 'All'
        )
    ''')
    
    # 2. Items & Inventory
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            item_code TEXT PRIMARY KEY,
            item_name TEXT NOT NULL,
            category TEXT NOT NULL,
            unit TEXT NOT NULL,
            current_stock REAL DEFAULT 0,
            unit_price REAL DEFAULT 0
        )
    ''')
    
    # 3. Orders Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_date TEXT DEFAULT CURRENT_TIMESTAMP,
            customer_name TEXT NOT NULL,
            target_item_code TEXT,
            ordered_quantity REAL NOT NULL,
            current_stage TEXT DEFAULT 'قسم الطباعة',
            order_status TEXT DEFAULT 'قيد التنفيذ',
            invoice_no TEXT,
            FOREIGN KEY(target_item_code) REFERENCES items(item_code)
        )
    ''')
    
    # 4. Purchases Invoices (فواتير الشراء)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchases (
            purchase_id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT UNIQUE NOT NULL,
            supplier_name TEXT NOT NULL,
            item_code TEXT,
            quantity REAL NOT NULL,
            unit_price REAL NOT NULL,
            total_amount REAL,
            purchase_date TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(item_code) REFERENCES items(item_code)
        )
    ''')
    
    # 5. Sales Invoices (فواتير البيع)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT UNIQUE NOT NULL,
            order_id INTEGER,
            customer_name TEXT NOT NULL,
            total_amount REAL NOT NULL,
            sale_date TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(order_id) REFERENCES orders(order_id)
        )
    ''')
    
    # 6. Inventory Vouchers (سندات الصرف والقبض المخزني)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory_vouchers (
            voucher_id INTEGER PRIMARY KEY AUTOINCREMENT,
            voucher_type TEXT NOT NULL, -- سند صرف, سند قبض
            item_code TEXT,
            quantity REAL NOT NULL,
            notes TEXT,
            voucher_date TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(item_code) REFERENCES items(item_code)
        )
    ''')
    
    # 7. Worker Tasks & Wages
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS worker_tasks (
            task_id INTEGER PRIMARY KEY AUTOINCREMENT,
            worker_username TEXT,
            order_id INTEGER,
            task_name TEXT NOT NULL,
            quantity_done REAL NOT NULL,
            piece_rate REAL DEFAULT 0.0,
            total_wage REAL GENERATED ALWAYS AS (quantity_done * piece_rate) VIRTUAL,
            task_date TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(order_id) REFERENCES orders(order_id)
        )
    ''')
    
    # Seed default admin if empty
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
    st.markdown("<h1 style='text-align: center; color: #1F4E78;'>🖨️ نظام المطبعة الشامل والذكي</h1>", unsafe_allow_html=True)
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

menu_options = [
    "📊 لوحة المؤشرات والتحكم",
    "📦 إدارة المخزون والأصناف",
    "📥 فواتير وسندات المخزن",
    "📋 إدارة الطلبيات والإنتاج",
    "💰 فواتير البيع والمخرجات",
    "⚙️ متابعة سير العمل ومراحل الإنتاج",
    "👥 تقارير وأجور العاملين",
    "🔐 إعدادات الحساب وكلمة المرور"
]

if role == "Admin":
    menu_options.append("🛠️ إدارة المستخدمين والصلاحيات الشاملة")

menu = st.sidebar.radio("القائمة الرئيسية", menu_options)

if st.sidebar.button("🚪 تسجيل الخروج", use_container_width=True):
    st.session_state["logged_in"] = False
    st.rerun()

conn = get_connection()

# ================= 1. DASHBOARD =================
if menu == "📊 لوحة المؤشرات والتحكم":
    st.title("📊 لوحة المؤشرات والتحكم الشاملة")
    st.markdown("---")
    
    total_orders = pd.read_sql("SELECT COUNT(*) FROM orders", conn).iloc[0, 0]
    total_items = pd.read_sql("SELECT COUNT(*) FROM items", conn).iloc[0, 0]
    total_sales = pd.read_sql("SELECT SUM(total_amount) FROM sales", conn).iloc[0, 0] or 0.0
    total_wages = pd.read_sql("SELECT SUM(total_wage) FROM worker_tasks", conn).iloc[0, 0] or 0.0
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("إجمالي الطلبيات", total_orders)
    col2.metric("عدد الأصناف بالمستودع", total_items)
    col3.metric("إجمالي المبيعات", f"{total_sales:,.2f} ر.س")
    col4.metric("إجمالي أجور العمال", f"{total_wages:,.2f} ر.س")
    
    st.markdown("### 🚀 حالة سير العمل ومراحل الطلبيات")
    df_o = pd.read_sql("SELECT order_id AS 'رقم الطلبية', customer_name AS 'العميل', ordered_quantity AS 'الكمية', current_stage AS 'المرحلة الحالية', order_status AS 'الحالة' FROM orders", conn)
    st.dataframe(df_o, use_container_width=True)

# ================= 2. INVENTORY & ITEMS (Add, Edit, Delete) =================
elif menu == "📦 إدارة المخزون والأصناف":
    st.title("📦 إدارة الأصناف والمخزون (إضافة، تعديل، حذف)")
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["قائمة الأصناف الحالية", "إضافة صنف جديد", "تعديل أو حذف صنف"])
    
    with tab1:
        df_items = pd.read_sql("SELECT item_code AS 'كود الصنف', item_name AS 'اسم الصنف', category AS 'التصنيف', unit AS 'الوحدة', current_stock AS 'الرصيد الحالي', unit_price AS 'السعر' FROM items", conn)
        st.dataframe(df_items, use_container_width=True)
        
    with tab2:
        if role == "Admin" or "Inventory" in allowed or allowed == "All":
            with st.form("add_item"):
                c1, c2 = st.columns(2)
                with c1:
                    icode = st.text_input("كود الصنف (مثال: RM-01)")
                    iname = st.text_input("اسم الصنف")
                    cat = st.selectbox("التصنيف", ["مادة خام", "منتج نهائي"])
                with c2:
                    unit = st.text_input("الوحدة (رزمة، قطعة، لتر)")
                    stock = st.number_input("الرصيد الابتدائي", min_value=0.0, value=0.0)
                    price = st.number_input("سعر الوحدة", min_value=0.0, value=0.0)
                
                if st.form_submit_button("حفظ الصنف الجديد"):
                    try:
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO items VALUES (?, ?, ?, ?, ?, ?)", (icode, iname, cat, unit, stock, price))
                        conn.commit()
                        st.success("تم إضافة الصنف بنجاح!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"خطأ: الكود موجود مسبقاً ({e})")
        else:
            st.warning("ليس لديك صلاحية لإضافة أصناف.")

    with tab3:
        if role == "Admin" or allowed == "All":
            items_list = pd.read_sql("SELECT item_code, item_name FROM items", conn)
            if not items_list.empty:
                sel_item = st.selectbox("اختر الصنف للتعديل أو الحذف", options=items_list['item_code'].tolist(), format_func=lambda x: items_list[items_list['item_code'] == x]['item_name'].values[0])
                current_data = pd.read_sql(f"SELECT * FROM items WHERE item_code = '{sel_item}'", conn).iloc[0]
                
                with st.form("edit_item_form"):
                    new_name = st.text_input("اسم الصنف الجديد", value=current_data['item_name'])
                    new_price = st.number_input("سعر الوحدة الجديد", value=float(current_data['unit_price']))
                    new_stock = st.number_input("تعديل الرصيد الحالي", value=float(current_data['current_stock']))
                    
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        update_btn = st.form_submit_button("تعديل بيانات الصنف")
                    with col_e2:
                        delete_btn = st.form_submit_button("حذف الصنف نهائياً")
                        
                    if update_btn:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE items SET item_name = ?, unit_price = ?, current_stock = ? WHERE item_code = ?", (new_name, new_price, new_stock, sel_item))
                        conn.commit()
                        st.success("تم تعديل بيانات الصنف بنجاح!")
                        st.rerun()
                    if delete_btn:
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM items WHERE item_code = ?", (sel_item,))
                        conn.commit()
                        st.success("تم حذف الصنف بنجاح!")
                        st.rerun()
        else:
            st.warning("هذه الصلاحية خاصة بمدير النظام.")

# ================= 3. PURCHASES & INVENTORY VOUCHERS =================
elif menu == "📥 فواتير وسندات المخزن":
    st.title("📥 فواتير الشراء وسندات الصرف والقبض المخزني")
    st.markdown("---")
    
    t1, t2, t3 = st.tabs(["فاتورة شراء (توريد)", "سند صرف / قبض مخزني", "تقارير حركة الصنف (وارد ومنصرف)"])
    
    with t1:
        with st.form("purchase_form"):
            st.subheader("إدخال فاتورة شراء مواد خام جديدة وزيادة رصيد المخزن")
            inv_no = st.text_input("رقم فاتورة المورد")
            supplier = st.text_input("اسم المورد")
            raw_items = pd.read_sql("SELECT item_code, item_name FROM items WHERE category = 'مادة خام'", conn)
            
            r_code = st.selectbox("المادة الخام", options=raw_items['item_code'].tolist(), format_func=lambda x: raw_items[raw_items['item_code'] == x]['item_name'].values[0]) if not raw_items.empty else None
            p_qty = st.number_input("الكمية المشتراة", min_value=1.0, value=50.0)
            u_price = st.number_input("سعر الوحدة", min_value=0.0, value=10.0)
            
            if st.form_submit_button("حفظ فاتورة الشراء وتحديث المخزن"):
                if r_code:
                    total_val = p_qty * u_price
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO purchases (invoice_no, supplier_name, item_code, quantity, unit_price, total_amount) VALUES (?, ?, ?, ?, ?, ?)", (inv_no, supplier, r_code, p_qty, u_price, total_val))
                    cursor.execute("UPDATE items SET current_stock = current_stock + ? WHERE item_code = ?", (p_qty, r_code))
                    conn.commit()
                    st.success("تم حفظ الفاتورة وتحديث رصيد المخزن بنجاح!")
                    st.rerun()
                    
    with t2:
        with st.form("voucher_form"):
            st.subheader("سندات الصرف والقبض المخزني اليدوية")
            v_type = st.selectbox("نوع السند", ["سند صرف مخزني", "سند قبض مخزني"])
            all_items = pd.read_sql("SELECT item_code, item_name FROM items", conn)
            v_item = st.selectbox("الصنف", options=all_items['item_code'].tolist(), format_func=lambda x: all_items[all_items['item_code'] == x]['item_name'].values[0]) if not all_items.empty else None
            v_qty = st.number_input("الكمية", min_value=1.0, value=10.0)
            v_notes = st.text_area("ملاحظات السند والسبب")
            
            if st.form_submit_button("تنفيذ السند وتحديث المخزن"):
                if v_item:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO inventory_vouchers (voucher_type, item_code, quantity, notes) VALUES (?, ?, ?, ?)", (v_type, v_item, v_qty, v_notes))
                    if v_type == "سند صرف مخزني":
                        cursor.execute("UPDATE items SET current_stock = current_stock - ? WHERE item_code = ?", (v_qty, v_item))
                    else:
                        cursor.execute("UPDATE items SET current_stock = current_stock + ? WHERE item_code = ?", (v_qty, v_item))
                    conn.commit()
                    st.success("تم تنفيذ السند وتحديث المخزن بنجاح!")
                    st.rerun()
                    
    with t3:
        st.subheader("تقرير حركة الوارد والمنصرف التفصيلي لكل صنف")
        all_itms = pd.read_sql("SELECT item_code, item_name FROM items", conn)
        if not all_itms.empty:
            sel_rep_item = st.selectbox("اختر الصنف لعرض حركته", options=all_itms['item_code'].tolist(), format_func=lambda x: all_itms[all_itms['item_code'] == x]['item_name'].values[0])
            
            st.markdown("#### 📥 المشتريات (الوارد)")
            df_pur = pd.read_sql(f"SELECT invoice_no AS 'رقم الفاتورة', supplier_name AS 'المورد', quantity AS 'الكمية الواردة', unit_price AS 'السعر', purchase_date AS 'التاريخ' FROM purchases WHERE item_code = '{sel_rep_item}'", conn)
            st.dataframe(df_pur, use_container_width=True)
            
            st.markdown("#### 📤 السندات والحركات المخزنية")
            df_vouch = pd.read_sql(f"SELECT voucher_type AS 'نوع السند', quantity AS 'الكمية', notes AS 'الملاحظات', voucher_date AS 'التاريخ' FROM inventory_vouchers WHERE item_code = '{sel_rep_item}'", conn)
            st.dataframe(df_vouch, use_container_width=True)

# ================= 4. ORDERS MANAGEMENT =================
elif menu == "📋 إدارة الطلبيات والإنتاج":
    st.title("📋 إدارة الطلبيات وسير العمل")
    st.markdown("---")
    
    with st.form("new_order"):
        c_name = st.text_input("اسم العميل / جهة الطلب")
        finished_items = pd.read_sql("SELECT item_code, item_name FROM items WHERE category = 'منتج نهائي'", conn)
        t_item = st.selectbox("الصنف المطلوب إنتاجه", options=finished_items['item_code'].tolist(), format_func=lambda x: finished_items[finished_items['item_code'] == x]['item_name'].values[0]) if not finished_items.empty else None
        o_qty = st.number_input("الكمية المطلوبة", min_value=1.0, value=100.0)
        
        if st.form_submit_button("إرسال الطلبية وبدء التشغيل"):
            if t_item:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO orders (customer_name, target_item_code, ordered_quantity, current_stage, order_status) VALUES (?, ?, ?, 'قسم الطباعة', 'قيد التنفيذ')", (c_name, t_item, o_qty))
                conn.commit()
                st.success("تم إنشاء الطلبية بنجاح!")
                st.rerun()
                
    st.markdown("### سجل الطلبيات النشطة")
    df_ords = pd.read_sql("SELECT order_id AS 'رقم الطلبية', customer_name AS 'العميل', ordered_quantity AS 'الكمية', current_stage AS 'المرحلة الحالية', order_status AS 'الحالة' FROM orders", conn)
    st.dataframe(df_ords, use_container_width=True)

# ================= 5. SALES & INVOICES =================
elif menu == "💰 فواتير البيع والمخرجات":
    st.title("💰 مخرجات الإنتاج وفواتير البيع النهائية")
    st.markdown("---")
    
    ready_ords = pd.read_sql("SELECT order_id, customer_name FROM orders WHERE invoice_no IS NULL", conn)
    
    with st.form("sale_invoice_form"):
        st.subheader("إصدار فاتورة بيع نهائية وإغلاق الطلبية")
        s_ord = st.selectbox("الطلبية المكتملة", options=ready_ords['order_id'].tolist(), format_func=lambda x: f"طلبية #{x} - {ready_ords[ready_ords['order_id'] == x]['customer_name'].values[0]}") if not ready_ords.empty else None
        inv_n = st.text_input("رقم فاتورة البيع (مثال: INV-9001)")
        tot_amt = st.number_input("إجمالي مبلغ الفاتورة (ر.س)", min_value=0.0, value=1000.0)
        
        if st.form_submit_button("إصدار الفاتورة وإغلاق الطلبية"):
            if s_ord:
                cust = ready_ords[ready_ords['order_id'] == s_ord]['customer_name'].values[0]
                cursor = conn.cursor()
                cursor.execute("INSERT INTO sales (invoice_no, order_id, customer_name, total_amount) VALUES (?, ?, ?, ?)", (inv_n, s_ord, cust, tot_amt))
                cursor.execute("UPDATE orders SET invoice_no = ?, order_status = 'مكتملة ومسلمة' WHERE order_id = ?", (inv_n, s_ord))
                conn.commit()
                st.success("تم إصدار الفاتورة وإغلاق الطلبية بنجاح!")
                st.rerun()
                
    st.markdown("### سجل فواتير المبيعات الصادرة")
    df_sales = pd.read_sql("SELECT invoice_no AS 'رقم الفاتورة', order_id AS 'رقم الطلبية', customer_name AS 'العميل', total_amount AS 'المبلغ (ر.س)', sale_date AS 'التاريخ' FROM sales", conn)
    st.dataframe(df_sales, use_container_width=True)

# ================= 6. PRODUCTION WORKFLOW TRACKING =================
elif menu == "⚙️ متابعة سير العمل ومراحل الإنتاج":
    st.title("⚙️ متابعة سير العمل ومراحل الإنتاج")
    st.markdown("---")
    
    act_ords = pd.read_sql("SELECT order_id, customer_name FROM orders WHERE order_status = 'قيد التنفيذ'", conn)
    if not act_ords.empty:
        with st.form("stage_form"):
            up_ord = st.selectbox("رقم الطلبية", options=act_ords['order_id'].tolist(), format_func=lambda x: f"طلبية #{x} - {act_ords[act_ords['order_id'] == x]['customer_name'].values[0]}")
            stg = st.selectbox("المرحلة الإنتاجية", ["قسم الطباعة", "قسم الفرز والتدبيس", "قسم التغرية والتعريش", "قسم البنر وسلك سكرين", "مكتملة تماماً"])
            
            if st.form_submit_button("تحديث مرحلة الط
