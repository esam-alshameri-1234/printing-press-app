import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="نظام المطبعة الذكي - تطبيق الأندرويد والإدارة",
    page_icon="📱",
    layout="wide"
)

DB_NAME = "printing_press_mobile.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Users Table with specific roles
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            department TEXT NOT NULL,
            role TEXT NOT NULL -- Admin, Inventory_Clerk, Order_Clerk, Worker
        )
    ''')
    
    # 2. Items & Inventory
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            item_code TEXT PRIMARY KEY,
            item_name TEXT NOT NULL,
            category TEXT NOT NULL, -- مادة خام, منتج نهائي
            unit TEXT NOT NULL,
            current_stock REAL DEFAULT 0,
            unit_price REAL DEFAULT 0
        )
    ''')
    
    # 3. Item Recipes (What raw materials an item needs)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS item_recipes (
            recipe_id INTEGER PRIMARY KEY AUTOINCREMENT,
            finished_item_code TEXT,
            raw_item_code TEXT,
            required_qty_per_unit REAL NOT NULL,
            FOREIGN KEY(finished_item_code) REFERENCES items(item_code),
            FOREIGN KEY(raw_item_code) REFERENCES items(item_code)
        )
    ''')
    
    # 4. Orders
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
    
    # 5. Worker Daily Tasks & Wages
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS worker_tasks (
            task_id INTEGER PRIMARY KEY AUTOINCREMENT,
            worker_username TEXT,
            order_id INTEGER,
            task_name TEXT NOT NULL,
            quantity_done REAL NOT NULL,
            piece_rate REAL DEFAULT 0.0, -- الأجر لكل وحدة
            total_wage REAL GENERATED ALWAYS AS (quantity_done * piece_rate) VIRTUAL,
            task_date TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(order_id) REFERENCES orders(order_id)
        )
    ''')
    
    # Seed default users if empty
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO users (username, password, full_name, department, role) VALUES (?, ?, ?, ?, ?)", [
            ("admin", "1234", "مدير النظام العام", "الإدارة العليا", "Admin"),
            ("inv_man", "2222", "مسؤول المخزون", "المستودع", "Inventory_Clerk"),
            ("ord_man", "3333", "مسؤول الطلبيات", "خدمة العملاء", "Order_Clerk"),
            ("khaled", "1111", "خالد عمر (عامل طباعة)", "قسم الطباعة", "Worker"),
            ("saeed", "4444", "سعيد محمود (عامل فرز)", "قسم الفرز والتدبيس", "Worker")
        ])
        
    # Seed default items if empty
    cursor.execute("SELECT COUNT(*) FROM items")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO items (item_code, item_name, category, unit, current_stock, unit_price) VALUES (?, ?, ?, ?, ?, ?)", [
            ("RM-01", "ورق كوشيه 150 جرام", "مادة خام", "رزمة", 1000, 150.0),
            ("RM-02", "أحبار أوفست سوداء", "مادة خام", "لتر", 100, 80.0),
            ("FG-01", "بروشورات إعلانية", "منتج نهائي", "قطعة", 0, 2.5),
            ("FG-02", "فواتير ضريبية", "منتج نهائي", "دفتر", 0, 20.0)
        ])
        
    conn.commit()
    conn.close()

init_db()

# Session state
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.session_state["full_name"] = ""
    st.session_state["role"] = ""

# --- LOGIN SCREEN ---
if not st.session_state["logged_in"]:
    st.markdown("<h1 style='text-align: center; color: #1F4E78;'>📱 نظام المطبعة الذكي (تطبيق الهاتف والإدارة)</h1>", unsafe_allow_html=True)
    st.markdown("<h4 style='text-align: center; color: gray;'>تسجيل الدخول الموحد للعمال والمشرفين</h4>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("اسم المستخدم")
            password = st.text_input("كلمة المرور", type="password")
            submit = st.form_submit_button("تسجيل الدخول", use_container_width=True)
            
            if submit:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT full_name, role, department FROM users WHERE username = ? AND password = ?", (username, password))
                user = cursor.fetchone()
                conn.close()
                
                if user:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = username
                    st.session_state["full_name"] = user[0]
                    st.session_state["role"] = user[1]
                    st.success("تم تسجيل الدخول بنجاح!")
                    st.rerun()
                else:
                    st.error("اسم المستخدم أو كلمة المرور غير صحيحة!")
                    
        st.info("""💡 **حسابات تجريبية للاختبار الفوري:**

- **مدير التطبيق:** `admin` / `1234`

- **مسؤول المواد الخام:** `inv_man` / `2222`

- **مسؤول الطلبيات:** `ord_man` / `3333`

- **عامل (خالد):** `khaled` / `1111`""")
    st.stop()

# --- SIDEBAR NAVIGATION BASED ON ROLES ---
role = st.session_state["role"]
full_name = st.session_state["full_name"]

st.sidebar.title(f"👤 {full_name}")
st.sidebar.markdown(f"**الصلاحية:** `{role}`")
st.sidebar.markdown("---")

menu_options = []

if role == "Admin":
    menu_options = [
        "📊 لوحة المؤشرات والتقارير الشاملة",
        "📦 إدارة الأصناف والمخزون",
        "📋 إدارة الطلبيات ووصفات المواد",
        "⚙️ متابعة سير العمل ومراحل الإنتاج",
        "💰 تقارير أجور العاملين والإنتاج",
        "👥 إدارة المستخدمين والصلاحيات"
    ]
elif role == "Inventory_Clerk":
    menu_options = [
        "📦 إدارة الأصناف والمخزون",
        "📊 عرض المخزون الحالي"
    ]
elif role == "Order_Clerk":
    menu_options = [
        "📋 إدارة الطلبيات ووصفات المواد",
        "📦 عرض الأصناف المتاحة"
    ]
elif role == "Worker":
    menu_options = [
        "📝 تسجيل أعمالي اليومية (تلفون العامل)",
        "📊 استعراض مهامي السابقة وأجوري"
    ]

menu = st.sidebar.radio("القائمة الرئيسية", menu_options)

if st.sidebar.button("🚪 تسجيل الخروج", use_container_width=True):
    st.session_state["logged_in"] = False
    st.rerun()

conn = get_connection()

# ================= ADMIN DASHBOARD & REPORTS =================
if menu == "📊 لوحة المؤشرات والتقارير الشاملة":
    st.title("📊 لوحة المؤشرات والتحكم الشاملة لمدير التطبيق")
    st.markdown("---")
    
    total_orders = pd.read_sql("SELECT COUNT(*) FROM orders", conn).iloc[0, 0]
    active_orders = pd.read_sql("SELECT COUNT(*) FROM orders WHERE order_status = 'قيد التنفيذ'", conn).iloc[0, 0]
    total_workers = pd.read_sql("SELECT COUNT(*) FROM users WHERE role = 'Worker'", conn).iloc[0, 0]
    total_wages = pd.read_sql("SELECT SUM(total_wage) FROM worker_tasks", conn).iloc[0, 0] or 0.0
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("إجمالي الطلبيات", total_orders)
    col2.metric("الطلبيات قيد التنفيذ", active_orders)
    col3.metric("عدد العاملين", total_workers)
    col4.metric("إجمالي أجور العمال المحسوبة", f"{total_wages:,.2f} ر.س")
    
    st.markdown("### 🚀 حالة الطلبيات الحالية وسير العمل بالمراحل")
    df_orders = pd.read_sql("SELECT order_id AS 'رقم الطلبية', customer_name AS 'اسم العميل', ordered_quantity AS 'الكمية', current_stage AS 'المرحلة الحالية', order_status AS 'الحالة' FROM orders", conn)
    st.dataframe(df_orders, use_container_width=True)

# ================= INVENTORY & ITEMS MANAGEMENT =================
elif menu in ["📦 إدارة الأصناف والمخزون", "📊 عرض المخزون الحالي"]:
    st.title("📦 إدارة الأصناف والمخزون (صلاحية مسؤول المواد الخام)")
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["مستودع الأصناف الحالي", "إضافة صنف جديد / تعديل رصيد"])
    
    with tab1:
        df_items = pd.read_sql("SELECT item_code AS 'كود الصنف', item_name AS 'اسم الصنف', category AS 'التصنيف', unit AS 'الوحدة', current_stock AS 'الرصيد الحالي', unit_price AS 'السعر' FROM items", conn)
        st.dataframe(df_items, use_container_width=True)
        
    with tab2:
        if role in ["Admin", "Inventory_Clerk"]:
            with st.form("add_item_form"):
                col1, col2 = st.columns(2)
                with col1:
                    item_code = st.text_input("كود الصنف (مثال: RM-03 أو FG-03)")
                    item_name = st.text_input("اسم الصنف")
                    category = st.selectbox("التصنيف", ["مادة خام", "منتج نهائي"])
                with col2:
                    unit = st.text_input("الوحدة (رزمة، قطعة، لتر، دفتر)")
                    current_stock = st.number_input("الرصيد الابتدائي", min_value=0.0, value=0.0)
                    unit_price = st.number_input("سعر الوحدة", min_value=0.0, value=0.0)
                    
                submitted = st.form_submit_button("حفظ وصفي الصنف في النظام")
                if submitted:
                    try:
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO items VALUES (?, ?, ?, ?, ?, ?)", (item_code, item_name, category, unit, current_stock, unit_price))
                        conn.commit()
                        st.success("تم حفظ الصنف بنجاح!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"خطأ: كود الصنف موجود مسبقاً ({e})")
        else:
            st.warning("ليس لديك صلاحية لإضافة أو تعديل الأصناف (هذه الصلاحية لمسؤول المخزون).")

# ================= ORDERS & RECIPES MANAGEMENT =================
elif menu in ["📋 إدارة الطلبيات ووصفات المواد", "📦 عرض الأصناف المتاحة"]:
    st.title("📋 إدارة الطلبيات وتحديد المواد الخام المطلوبة لكل صنف")
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["إدخال طلبية جديدة", "وصفة المواد الخام لكل صنف"])
    
    with tab1:
        with st.form("new_order_form"):
            customer_name = st.text_input("اسم العميل / جهة الطلب")
            products = pd.read_sql("SELECT item_code, item_name FROM items WHERE category = 'منتج نهائي'", conn)
            
            if products.empty:
                st.warning("يرجى إضافة منتجات نهائية للمستودع أولاً.")
                target_item = None
            else:
                target_item = st.selectbox("الصنف المطلوب إنتاجه", options=products['item_code'].tolist(), format_func=lambda x: products[products['item_code'] == x]['item_name'].values[0])
            
            ordered_qty = st.number_input("الكمية المطلوبة", min_value=1.0, value=100.0)
            
            submit_ord = st.form_submit_button("إرسال الطلبية وبدء دورة العمل")
            if submit_ord and target_item:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO orders (customer_name, target_item_code, ordered_quantity, current_stage, order_status) VALUES (?, ?, ?, 'قسم الطباعة', 'قيد التنفيذ')", (customer_name, target_item, ordered_qty))
                conn.commit()
                st.success("تم إنشاء الطلبية بنجاح وسير العمل جاري عبر الأقسام!")
                st.rerun()
                
        st.markdown("### قائمة الطلبيات النشطة")
        df_ord = pd.read_sql("SELECT order_id AS 'رقم الطلبية', customer_name AS 'العميل', ordered_quantity AS 'الكمية', current_stage AS 'المرحلة' FROM orders WHERE order_status = 'قيد التنفيذ'", conn)
        st.dataframe(df_ord, use_container_width=True)
        
    with tab2:
        st.markdown("### ربط المنتجات النهائية بالمواد الخام اللازمة")
        with st.form("recipe_form"):
            finished_items = pd.read_sql("SELECT item_code, item_name FROM items WHERE category = 'منتج نهائي'", conn)
            raw_items = pd.read_sql("SELECT item_code, item_name FROM items WHERE category = 'مادة خام'", conn)
            
            f_item = st.selectbox("المنتج النهائي", options=finished_items['item_code'].tolist(), format_func=lambda x: finished_items[finished_items['item_code'] == x]['item_name'].values[0]) if not finished_items.empty else None
            r_item = st.selectbox("المادة الخام المطلوبة", options=raw_items['item_code'].tolist(), format_func=lambda x: raw_items[raw_items['item_code'] == x]['item_name'].values[0]) if not raw_items.empty else None
            req_qty = st.number_input("الكمية اللازمة لكل وحدة منتج", min_value=0.01, value=1.0)
            
            save_recipe = st.form_submit_button("حفظ وصفة الصنف")
            if save_recipe and f_item and r_item:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO item_recipes (finished_item_code, raw_item_code, required_qty_per_unit) VALUES (?, ?, ?)", (f_item, r_item, req_qty))
                conn.commit()
                st.success("تم حفظ وصفة المواد الخام بنجاح!")
                st.rerun()

# ================= WORKER DAILY TASKS & MOBILE LOGGING =================
elif menu in ["📝 تسجيل أعمالي اليومية (تلفون العامل)", "📊 استعراض مهامي السابقة وأجوري"]:
    st.title("📱 شاشة تسجيل الأعمال اليومية للعامل (من الهاتف)")
    st.markdown("---")
    
    with st.form("worker_task_form"):
        st.markdown(f"**العامل المجدول:** {full_name}")
        orders_active = pd.read_sql("SELECT order_id, customer_name FROM orders WHERE order_status = 'قيد التنفيذ'", conn)
        
        ord_sel = st.selectbox("رقم الطلبية المرتبطة بالعمل", options=orders_active['order_id'].tolist(), format_func=lambda x: f"طلبية رقم #{x} - {orders_active[orders_active['order_id'] == x]['customer_name'].values[0]}") if not orders_active.empty else None
        
        task_name = st.text_input("وصف المهمة المنجزة (مثال: طباعة أوفست، فرز، تغرية)")
        quantity_done = st.number_input("الكمية التي أنجزتها اليوم", min_value=1.0, value=100.0)
        piece_rate = st.number_input("أجر القطعة الواحدة (ر.س) - يحددها المدير", min_value=0.0, value=0.5)
        
        submit_task = st.form_submit_button("إرسال وسداده في سجلي اليومي")
        if submit_task and ord_sel:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO worker_tasks (worker_username, order_id, task_name, quantity_done, piece_rate) VALUES (?, ?, ?, ?, ?)", (st.session_state["username"], ord_sel, task_name, quantity_done, piece_rate))
            conn.commit()
            st.success("تم تسجيل عملك اليومي بنجاح وحسابه في الأجور!")
            st.rerun()
            
    st.markdown("### 📈 سجل أعمالك السابقة وإجمالي أجورك المحسوبة")
    df_my_tasks = pd.read_sql(f"SELECT order_id AS 'رقم الطلبية', task_name AS 'المهمة', quantity_done AS 'الكمية المنجزة', piece_rate AS 'أجر القطعة', total_wage AS 'إجمالي الأجر (ر.س)', task_date AS 'التاريخ' FROM worker_tasks WHERE worker_username = '{st.session_state['username']}'", conn)
    st.dataframe(df_my_tasks, use_container_width=True)

# ================= WORKERS WAGES & PERFORMANCE REPORTS (ADMIN) =================
elif menu == "💰 تقارير أجور العاملين والإنتاج":
    st.title("💰 تقارير أجور العاملين والإنتاج اليومي والشهرية (للإدارة)")
    st.markdown("---")
    
    st.markdown("### ملخص أجور العمال حسب المهام والكميات")
    df_all_wages = pd.read_sql("""
        SELECT worker_username AS 'اسم المستخدم', order_id AS 'رقم الطلبية', task_name AS 'المهمة', quantity_done AS 'الكمية', piece_rate AS 'أجر القطعة', total_wage AS 'إجمالي الأجر (ر.س)', task_date AS 'التاريخ'
        FROM worker_tasks
    """, conn)
    st.dataframe(df_all_wages, use_container_width=True)
    
    if not df_all_wages.empty:
        st.markdown("### 📊 إجمالي المستحقات المالية لكل عامل")
        df_summary = df_all_wages.groupby('اسم المستخدم')['إجمالي الأجر (ر.س)'].sum().reset_index()
        st.dataframe(df_summary, use_container_width=True)

# ================= WORKFLOW & STAGES TRACKING =================
elif menu == "⚙️ متابعة سير العمل ومراحل الإنتاج":
    st.title("⚙️ متابعة سير العمل وتتبع مراحل الإنتاج")
    st.markdown("---")
    
    orders_list = pd.read_sql("SELECT order_id, customer_name FROM orders WHERE order_status = 'قيد التنفيذ'", conn)
    if not orders_list.empty:
        with st.form("stage_update_form"):
            ord_id = st.selectbox("اختر الطلبية لتحديث مرحلتها", options=orders_list['order_id'].tolist(), format_func=lambda x: f"طلبية #{x} - {orders_list[orders_list['order_id'] == x]['customer_name'].values[0]}")
            new_stage = st.selectbox("المرحلة الإنتاجية الجديدة", ["قسم الطباعة", "قسم الفرز والتدبيس", "قسم التغرية والتعريش", "قسم البنر وسلك سكرين", "جاهز للتسليم ومكتمل"])
            
            update_btn = st.form_submit_button("تحديث مرحلة الطلبية الفورية")
            if update_btn:
                cursor = conn.cursor()
                cursor.execute("UPDATE orders SET current_stage = ? WHERE order_id = ?", (new_stage, ord_id))
                if new_stage == "جاهز للتسليم ومكتمل":
                    cursor.execute("UPDATE orders SET order_status = 'مكتملة ومسلمة' WHERE order_id = ?", (ord_id,))
                conn.commit()
                st.success("تم تحديث مرحلة الطلبية بنجاح!")
                st.rerun()

    st.markdown("### جدول سير الطلبيات الحالي")
    df_flow = pd.read_sql("SELECT order_id AS 'رقم الطلبية', customer_name AS 'العميل', current_stage AS 'المرحلة الحالية', order_status AS 'الحالة' FROM orders", conn)
    st.dataframe(df_flow, use_container_width=True)

# ================= USERS MANAGEMENT =================
elif menu == "👥 إدارة المستخدمين والصلاحيات":
    st.title("👥 إدارة مستخدمي التطبيق والصلاحيات (مدير النظام)")
    st.markdown("---")
    
    with st.form("new_user_form"):
        col1, col2 = st.columns(2)
        with col1:
            new_user = st.text_input("اسم المستخدم لتسجيل الدخول")
            new_pass = st.text_input("كلمة المرور")
            full_name_u = st.text_input("الاسم الكامل للعامل أو المسؤول")
        with col2:
            dept = st.text_input("القسم أو الوظيفة")
            role_sel = st.selectbox("صلاحية الحساب في التطبيق", ["Admin", "Inventory_Clerk", "Order_Clerk", "Worker"])
            
        add_u = st.form_submit_button("إضافة مستخدم جديد للنظام")
        if add_u:
            try:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO users (username, password, full_name, department, role) VALUES (?, ?, ?, ?, ?)", (new_user, new_pass, full_name_u, dept, role_sel))
                conn.commit()
                st.success("تمت إضافة المستخدم بنجاح!")
                st.rerun()
            except Exception as e:
                st.error(f"خطأ: اسم المستخدم موجود مسبقاً ({e})")
                
    st.markdown("### قائمة المستخدمين والصلاحيات الحالية")
    df_usrs = pd.read_sql("SELECT username AS 'اسم المستخدم', full_name AS 'الاسم الكامل', department AS 'القسم', role AS 'الصلاحية' FROM users", conn)
    st.dataframe(df_usrs, use_container_width=True)

conn.close()
