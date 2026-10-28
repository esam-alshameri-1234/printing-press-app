import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="نظام المطبعة الشامل والذكي (ERP)",
    page_icon="🖨️",
    layout="wide"
)

DB_NAME = "printing_press_enterprise.db"

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
    
    # 4. Purchases Header & Details
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchase_invoices (
            inv_id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT UNIQUE NOT NULL,
            supplier_name TEXT NOT NULL,
            purchase_date TEXT DEFAULT CURRENT_TIMESTAMP,
            total_invoice_amount REAL DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchase_items (
            p_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT NOT NULL,
            item_code TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit_price REAL NOT NULL,
            total_price REAL NOT NULL,
            FOREIGN KEY(invoice_no) REFERENCES purchase_invoices(invoice_no),
            FOREIGN KEY(item_code) REFERENCES items(item_code)
        )
    ''')
    
    # 5. Sales Header & Details
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales_invoices (
            s_inv_id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT UNIQUE NOT NULL,
            order_id INTEGER,
            customer_name TEXT NOT NULL,
            sale_date TEXT DEFAULT CURRENT_TIMESTAMP,
            total_invoice_amount REAL DEFAULT 0,
            FOREIGN KEY(order_id) REFERENCES orders(order_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales_items (
            s_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT NOT NULL,
            item_code TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit_price REAL NOT NULL,
            total_price REAL NOT NULL,
            FOREIGN KEY(invoice_no) REFERENCES sales_invoices(invoice_no),
            FOREIGN KEY(item_code) REFERENCES items(item_code)
        )
    ''')
    
    # 6. Inventory Vouchers
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory_vouchers (
            voucher_id INTEGER PRIMARY KEY AUTOINCREMENT,
            voucher_type TEXT NOT NULL,
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
    st.markdown("<h1 style='text-align: center; color: #1F4E78;'>🖨️ نظام المطبعة الشامل والذكي (ERP)</h1>", unsafe_allow_html=True)
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
    "📥 فواتير الشراء متعددة الأصناف",
    "💰 فواتير البيع متعددة الأصناف",
    "📋 إدارة الطلبيات والإنتاج",
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
    total_sales = pd.read_sql("SELECT SUM(total_invoice_amount) FROM sales_invoices", conn).iloc[0, 0] or 0.0
    total_wages = pd.read_sql("SELECT SUM(total_wage) FROM worker_tasks", conn).iloc[0, 0] or 0.0
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("إجمالي الطلبيات", total_orders)
    col2.metric("عدد الأصناف بالمستودع", total_items)
    col3.metric("إجمالي المبيعات", f"{total_sales:,.2f} ر.س")
    col4.metric("إجمالي أجور العمال", f"{total_wages:,.2f} ر.س")
    
    st.markdown("### 🚀 حالة سير العمل ومراحل الطلبيات")
    df_o = pd.read_sql("SELECT order_id AS 'رقم الطلبية', customer_name AS 'العميل', ordered_quantity AS 'الكمية', current_stage AS 'المرحلة الحالية', order_status AS 'الحالة' FROM orders", conn)
    st.dataframe(df_o, use_container_width=True)

# ================= 2. INVENTORY & ITEMS =================
elif menu == "📦 إدارة المخزون والأصناف":
    st.title("📦 إدارة الأصناف والمخزون (إضافة، تعديل، حذف)")
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["قائمة الأصناف الحالية", "إضافة صنف جديد", "تعديل أو حذف صنف"])
    
    with tab1:
        df_items = pd.read_sql("SELECT item_code AS 'كود الصنف', item_name AS 'اسم الصنف', category AS 'التصنيف', unit AS 'الوحدة', current_stock AS 'الرصيد الحالي', unit_price AS 'السعر' FROM items", conn)
        st.dataframe(df_items, use_container_width=True)
        
    with tab2:
        if role == "Admin" or allowed == "All":
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

# ================= 3. MULTI-ITEM PURCHASE INVOICES =================
elif menu == "📥 فواتير الشراء متعددة الأصناف":
    st.title("📥 فواتير الشراء متعددة الأصناف (توريد مواد خام)")
    st.markdown("---")
    
    with st.form("multi_purchase_form"):
        st.subheader("رأس الفاتورة")
        p_inv_no = st.text_input("رقم فاتورة الشراء")
        p_supplier = st.text_input("اسم المورد")
        
        st.subheader("بنود الأصناف في الفاتورة")
        raw_items = pd.read_sql("SELECT item_code, item_name FROM items WHERE category = 'مادة خام'", conn)
        
        if raw_items.empty:
            st.warning("يرجى إضافة مواد خام للمستودع أولاً.")
        else:
            st.markdown("##### الصنف الأول")
            i1 = st.selectbox("اختر المادة الخام 1", options=raw_items['item_code'].tolist(), format_func=lambda x: raw_items[raw_items['item_code'] == x]['item_name'].values[0], key="i1")
            q1 = st.number_input("الكمية 1", min_value=0.0, value=0.0, key="q1")
            pr1 = st.number_input("سعر الوحدة 1", min_value=0.0, value=0.0, key="pr1")
            
            st.markdown("##### الصنف الثاني (اختياري)")
            i2 = st.selectbox("اختر المادة الخام 2", options=["لا يوجد"] + raw_items['item_code'].tolist(), format_func=lambda x: "لا يوجد" if x=="لا يوجد" else raw_items[raw_items['item_code'] == x]['item_name'].values[0], key="i2")
            q2 = st.number_input("الكمية 2", min_value=0.0, value=0.0, key="q2")
            pr2 = st.number_input("سعر الوحدة 2", min_value=0.0, value=0.0, key="pr2")
            
            st.markdown("##### الصنف الثالث (اختياري)")
            i3 = st.selectbox("اختر المادة الخام 3", options=["لا يوجد"] + raw_items['item_code'].tolist(), format_func=lambda x: "لا يوجد" if x=="لا يوجد" else raw_items[raw_items['item_code'] == x]['item_name'].values[0], key="i3")
            q3 = st.number_input("الكمية 3", min_value=0.0, value=0.0, key="q3")
            pr3 = st.number_input("سعر الوحدة 3", min_value=0.0, value=0.0, key="pr3")
            
            if st.form_submit_button("حفظ فاتورة الشراء وتحديث المخزن"):
                if p_inv_no and p_supplier:
                    try:
                        cursor = conn.cursor()
                        total_inv = 0
                        items_to_save = []
                        
                        if q1 > 0:
                            t1 = q1 * pr1
                            total_inv += t1
                            items_to_save.append((i1, q1, pr1, t1))
                            
                        if i2 != "لا يوجد" and q2 > 0:
                            t2 = q2 * pr2
                            total_inv += t2
                            items_to_save.append((i2, q2, pr2, t2))
                            
                        if i3 != "لا يوجد" and q3 > 0:
                            t3 = q3 * pr3
                            total_inv += t3
                            items_to_save.append((i3, q3, pr3, t3))
                            
                        if items_to_save:
                            cursor.execute("INSERT INTO purchase_invoices (invoice_no, supplier_name, total_invoice_amount) VALUES (?, ?, ?)", (p_inv_no, p_supplier, total_inv))
                            for itm in items_to_save:
                                cursor.execute("INSERT INTO purchase_items (invoice_no, item_code, quantity, unit_price, total_price) VALUES (?, ?, ?, ?, ?)", (p_inv_no, itm[0], itm[1], itm[2], itm[3]))
                                cursor.execute("UPDATE items SET current_stock = current_stock + ? WHERE item_code = ?", (itm[1], itm[0]))
                            conn.commit()
                            st.success("تم حفظ فاتورة الشراء وتحديث أرصدة المخازن بنجاح!")
                            st.rerun()
                        else:
                            st.error("يرجى إدخال صنف واحد على الأقل بكمية صحيحة.")
                    except Exception as e:
                        st.error(f"خطأ: رقم الفاتورة موجود مسبقاً أو بيانات غير صحيحة ({e})")
                else:
                    st.warning("يرجى إدخال رقم الفاتورة واسم المورد.")

    st.markdown("### سجل فواتير الشراء السابقة")
    df_p_inv = pd.read_sql("SELECT invoice_no AS 'رقم الفاتورة', supplier_name AS 'المورد', total_invoice_amount AS 'إجمالي الفاتورة', purchase_date AS 'التاريخ' FROM purchase_invoices", conn)
    st.dataframe(df_p_inv, use_container_width=True)
# ================= 4. MULTI-ITEM SALES INVOICES =================
elif menu == "💰 فواتير البيع متعددة الأصناف":
    st.title("💰 فواتير البيع متعددة الأصناف والمخرجات")
    st.markdown("---")
    
    ready_ords = pd.read_sql("SELECT order_id, customer_name FROM orders WHERE invoice_no IS NULL", conn)
    
    with st.form("multi_sale_form"):
        st.subheader("إصدار فاتورة بيع مرتبطة بالطلبية ومشتملة على عدة اصناف")
        s_ord = st.selectbox("اختر الطلبية المكتملة", options=ready_ords['order_id'].tolist(), format_func=lambda x: f"طلبية #{x} - {ready_ords[ready_ords['order_id'] == s_ord]['customer_name'].values[0]}") if not ready_ords.empty else None
        s_inv_no = st.text_input("رقم فاتورة البيع النهائية")
        
        all_itms = pd.read_sql("SELECT item_code, item_name FROM items", conn)
        
        st.subheader("بنود الأصناف المباعة")
        if all_itms.empty:
            st.warning("لا توجد أصناف مسجلة.")
        else:
            s_i1 = st.selectbox("الصنف المباع 1", options=all_itms['item_code'].tolist(), format_func=lambda x: all_itms[all_itms['item_code'] == x]['item_name'].values[0], key="si1")
            s_q1 = st.number_input("الكمية المباعة 1", min_value=0.0, value=0.0, key="sq1")
            s_pr1 = st.number_input("سعر البيع للوحدة 1", min_value=0.0, value=0.0, key="spr1")
            
            s_i2 = st.selectbox("الصنف المباع 2 (اختياري)", options=["لا يوجد"] + all_itms['item_code'].tolist(), format_func=lambda x: "لا يوجد" if x=="لا يوجد" else all_itms[all_itms['item_code'] == x]['item_name'].values[0], key="si2")
            s_q2 = st.number_input("الكمية المباعة 2", min_value=0.0, value=0.0, key="sq2")
            s_pr2 = st.number_input("سعر البيع للوحدة 2", min_value=0.0, value=0.0, key="spr2")
            
            if st.form_submit_button("إصدار فاتورة البيع وإغلاق الطلبية"):
                if s_ord and s_inv_no:
                    try:
                        cust_name = ready_ords[ready_ords['order_id'] == s_ord]['customer_name'].values[0]
                        cursor = conn.cursor()
                        tot_sale = 0
                        s_items_to_save = []
                        
                        if s_q1 > 0:
                            st1 = s_q1 * s_pr1
                            tot_sale += st1
                            s_items_to_save.append((s_i1, s_q1, s_pr1, st1))
                            
                        if s_i2 != "لا يوجد" and s_q2 > 0:
                            st2 = s_q2 * s_pr2
                            tot_sale += st2
                            s_items_to_save.append((s_i2, s_q2, s_pr2, st2))
                            
                        if s_items_to_save:
                            cursor.execute("INSERT INTO sales_invoices (invoice_no, order_id, customer_name, total_invoice_amount) VALUES (?, ?, ?, ?)", (s_inv_no, s_ord, cust_name, tot_sale))
                            for sitm in s_items_to_save:
                                cursor.execute("INSERT INTO sales_items (invoice_no, item_code, quantity, unit_price, total_price) VALUES (?, ?, ?, ?, ?)", (s_inv_no, sitm[0], sitm[1], sitm[2], sitm[3]))
                            cursor.execute("UPDATE orders SET invoice_no = ?, order_status = 'مكتملة ومسلمة' WHERE order_id = ?", (s_inv_no, s_ord))
                            conn.commit()
                            st.success("تم إصدار فاتورة البيع وإغلاق الطلبية بنجاح!")
                            st.rerun()
                        else:
                            st.error("يرجى اختيار صنف مباع واحد على الأقل بكمية صحيحة.")
                    except Exception as e:
                        st.error(f"خطأ: رقم الفاتورة موجود مسبقاً ({e})")
                else:
                    st.warning("يرجى اختيار الطلبية وإدخال رقم الفاتورة.")

    st.markdown("### سجل فواتير المبيعات الصادرة")
    df_s_inv = pd.read_sql("SELECT invoice_no AS 'رقم الفاتورة', order_id AS 'رقم الطلبية', customer_name AS 'العميل', total_invoice_amount AS 'إجمالي الفاتورة', sale_date AS 'التاريخ' FROM sales_invoices", conn)
    st.dataframe(df_s_inv, use_container_width=True)

# ================= 5. ORDERS =================
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

# ================= 6. WORKFLOW =================
elif menu == "⚙️ متابعة سير العمل ومراحل الإنتاج":
    st.title("⚙️ متابعة سير العمل ومراحل الإنتاج")
    st.markdown("---")
    
    act_ords = pd.read_sql("SELECT order_id, customer_name FROM orders WHERE order_status = 'قيد التنفيذ'", conn)
    if not act_ords.empty:
        with st.form("stage_form"):
            up_ord = st.selectbox("رقم الطلبية", options=act_ords['order_id'].tolist(), format_func=lambda x: f"طلبية #{x} - {act_ords[act_ords['order_id'] == x]['customer_name'].values[0]}")
            stg = st.selectbox("المرحلة الإنتاجية", ["قسم الطباعة", "قسم الفرز والتدبيس", "قسم التغرية والتعريش", "قسم البنر وسلك سكرين", "مكتملة تماماً"])
            
            if st.form_submit_button("تحديث مرحلة الطلبية"):
                cursor = conn.cursor()
                cursor.execute("UPDATE orders SET current_stage = ? WHERE order_id = ?", (stg, up_ord))
                if stg == "مكتملة تماماً":
                    cursor.execute("UPDATE orders SET order_status = 'مكتملة ومسلمة' WHERE order_id = ?", (up_ord,))
                conn.commit()
                st.success("تم التحديث بنجاح!")
                st.rerun()
                
    st.markdown("### جدول سير العمل الحالي")
    df_flow = pd.read_sql("SELECT order_id AS 'رقم الطلبية', customer_name AS 'العميل', current_stage AS 'المرحلة', order_status AS 'الحالة' FROM orders", conn)
    st.dataframe(df_flow, use_container_width=True)

# ================= 7. WORKERS WAGES =================
elif menu == "👥 تقارير وأجور العاملين":
    st.title("👥 تسجيل أعمال العمال وتقارير الأجور اليومية والشهرية")
    st.markdown("---")
    
    if role == "Worker" or role == "Admin":
        with st.form("worker_task"):
            st.subheader("تسجيل إنجاز مهمة جديدة")
            ords_act = pd.read_sql("SELECT order_id, customer_name FROM orders WHERE order_status = 'قيد التنفيذ'", conn)
            o_sel = st.selectbox("الطلبية", options=ords_act['order_id'].tolist(), format_func=lambda x: f"طلبية #{x} - {ords_act[ords_act['order_id'] == x]['customer_name'].values[0]}") if not ords_act.empty else None
            t_name = st.text_input("اسم المهمة (مثال: طباعة أوفست، فرز)")
            q_done = st.number_input("الكمية المنجزة", min_value=1.0, value=100.0)
            p_rate = st.number_input("أجر القطعة (ر.س)", min_value=0.0, value=0.5)
            
            if st.form_submit_button("تسجيل المهمة وإضافتها لأجوري"):
                if o_sel:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO worker_tasks (worker_username, order_id, task_name, quantity_done, piece_rate) VALUES (?, ?, ?, ?, ?)", (st.session_state["username"], o_sel, t_name, q_done, p_rate))
                    conn.commit()
                    st.success("تم تسجيل المهمة وحساب الأجر بنجاح!")
                    st.rerun()
                    
    st.markdown("### سجل الأجور والمهام")
    if role == "Admin":
        df_tasks = pd.read_sql("SELECT task_id AS 'معرف المهمة', worker_username AS 'اسم المستخدم', order_id AS 'رقم الطلبية', task_name AS 'المهمة', quantity_done AS 'الكمية', piece_rate AS 'أجر القطعة', total_wage AS 'إجمالي الأجر', task_date AS 'التاريخ' FROM worker_tasks", conn)
    else:
        df_tasks = pd.read_sql(f"SELECT task_id AS 'معرف المهمة', order_id AS 'رقم الطلبية', task_name AS 'المهمة', quantity_done AS 'الكمية', piece_rate AS 'أجر القطعة', total_wage AS 'إجمالي الأجر', task_date AS 'التاريخ' FROM worker_tasks WHERE worker_username = '{st.session_state['username']}'", conn)
    st.dataframe(df_tasks, use_container_width=True)
    
    if role == "Admin" and not df_tasks.empty:
        st.markdown("#### 🛠️ تعديل أو حذف مهمة مسجلة (صلاحية الأدمن)")
        with st.form("edit_worker_task"):
            t_id_to_edit = st.number_input("أدخل معرف المهمة (Task ID) للتعديل أو الحذف", min_value=1, step=1)
            new_q = st.number_input("الكمية المعدلة", value=100.0)
            new_r = st.number_input("أجر القطعة المعدل", value=0.5)
            
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                edt_btn = st.form_submit_button("تعديل المهمة")
            with col_t2:
                del_btn = st.form_submit_button("حذف المهمة")
                
            if edt_btn:
                cursor = conn.cursor()
                cursor.execute("UPDATE worker_tasks SET quantity_done = ?, piece_rate = ? WHERE task_id = ?", (new_q, new_r, t_id_to_edit))
                conn.commit()
                st.success("تم تعديل المهمة بنجاح!")
                st.rerun()
            if del_btn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM worker_tasks WHERE task_id = ?", (t_id_to_edit,))
                conn.commit()
                st.success("تم حذف المهمة بنجاح!")
                st.rerun()
# ================= 8. PASSWORD CHANGE =================
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

# ================= 9. ADMIN USERS =================
elif menu == "🛠️ إدارة المستخدمين والصلاحيات الشاملة":
    if role != "Admin":
        st.error("عذراً، هذه الصفحة مخصصة لمدير النظام (Admin) فقط.")
    else:
        st.title("🛠️ إدارة المستخدمين والصلاحيات الشاملة (تحكم كامل)")
        st.markdown("---")
        
        with st.form("add_user_full"):
            st.subheader("إضافة مستخدم جديد وتحديد دوره")
            u_name = st.text_input("اسم المستخدم")
            u_pass = st.text_input("كلمة المرور")
            u_full = st.text_input("الاسم الكامل للعامل")
            u_dept = st.text_input("القسم")
            u_role = st.selectbox("الدور والصلاحية", ["Admin", "Inventory", "Worker"])
            
            if st.form_submit_button("إضافة المستخدم للنظام"):
                try:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO users (username, password, full_name, department, role, allowed_screens) VALUES (?, ?, ?, ?, ?, 'All')", (u_name, u_pass, u_full, u_dept, u_role))
                    conn.commit()
                    st.success("تم إضافة المستخدم بنجاح!")
                    st.rerun()
                except Exception as e:
                    st.error(f"خطأ: اسم المستخدم موجود مسبقاً ({e})")
                    
        st.markdown("### قائمة المستخدمين والصلاحيات الحالية")
        df_usr = pd.read_sql("SELECT username AS 'اسم المستخدم', full_name AS 'الاسم الكامل', department AS 'القسم', role AS 'الصلاحية' FROM users", conn)
        st.dataframe(df_usr, use_container_width=True)

conn.close()
