import sys
import os
import sqlite3
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtCore import QObject, pyqtSlot, QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt5.QtPrintSupport import QPrinter
from PyQt5.QtGui import QTextDocument
from PyQt5.QtGui import QIcon

msg = True

def resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class BackendHandler(QObject):
    def __init__(self, main_window, conn):
        super().__init__()
        self.main_window = main_window
        self.conn = conn
    
    def intstr(self, code: str):
        number = []
        letter = []
        num = ""
        char = ""
        
        for i in code:
            if i >= "0" and i<="9":
                num += i
                if char != "":
                    letter.append(char)
                    char = ""
                    
            elif (i >= "A" and i<="Z") or (i>="a" and i<="z"):
                if num != "":
                    number.append(num)
                    num = ""
                char += i
            
        if num != "":
            number.append(num)
            num = ""
            
        if char != "":
            letter.append(char)
            char = ""

        return number,letter
    
    @pyqtSlot(str)
    def print_invoice(self, html_content):
        try:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setPrinterName(printer_name)
            printer.setPageSize(QPrinter.A5)
            printer.setOrientation(QPrinter.Portrait)
            # pdf_css = """
            # <style>
            # table { border-collapse: collapse; width: 100%; }
            #     #productTable th, #productTable td { text-align: left; padding: 8px; border: 1px solid black; font-size: 80px; }
            # </style>
            # """
            # html_for_pdf = pdf_css + html_content

            pdf_css = """
            <style>
                @page { size: A4; margin: 0; }
                body { margin: 0; padding: 0; }
            </style>
            """
                # table { border-collapse: collapse; width: 100%; table-layout: fixed; }
                # td { border: 1px solid #000; text-align: center; padding: 5px; width: 25%; height: 90px; vertical-align: top; }
                # div { font-size: 10pt; margin-bottom: 5px; }
                # img { max-width: 100%; height: auto; }
            html_for_pdf = pdf_css + html_content
            doc = QTextDocument()
            doc.setHtml(html_for_pdf)
            doc.print_(printer)

            QMessageBox.information(self.main_window, "Printer", "Printed Successfully")
            self.main_window.browser.page().runJavaScript("clearInvoiceData();")
        except Exception as e:
            QMessageBox.warning(self.main_window, "Printer Error", "error: " + str(e))
        
    @pyqtSlot(str, int, str, str)
    def barcode(self, name, id, product_id, date):
        code = str(id)+str(product_id)+str(date)
        # from bar_print import printer
        from finsl import generate_barcode_html
        html = generate_barcode_html(code, name)
        self.print_invoice(html)
        # if printer_return == "success":
        #     QMessageBox.information(self.main_window, "Printer", "Printed Successfully")
        # else:
        #     QMessageBox.warning(self.main_window, "Printer Error", "Printer is not connected")


    @pyqtSlot(str, str)
    def login(self, username, password):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM accounts WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()
        if user:
            self.check_printer_on_start()
            self.open_dashboard()
        else:
            QMessageBox.warning(self.main_window, "Login Error", "Invalid username or password. Please try again.")
    
    def check_printer_on_start(self):
        global printer_name
        printer = QPrinter()
        printer_name = printer.printerName()
    
    @pyqtSlot()
    def logout(self):
        QApplication.quit()

    @pyqtSlot()
    def open_dashboard(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM accounts")
        user = cursor.fetchone()
        cursor.execute("SELECT * FROM customers")
        cust = cursor.fetchall()
        cursor.execute("SELECT * FROM products")
        prod = cursor.fetchall()
        file_path = resource_path("frontend/dashboard.html")
        url = QUrl.fromLocalFile(file_path)
        url.setQuery(f"username={user[1]}&cust={len(cust)}&pro={len(prod)}")
        self.main_window.browser.load(url)
    
    @pyqtSlot()
    def open_billing(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM accounts")
        user = cursor.fetchone()
        cursor.execute("select * from customers order by id desc limit 1")
        last_bill = cursor.fetchone()
        if last_bill:
            billno = last_bill[1]
            billno = int(billno.replace('A',"")) + 1
            billno = f"A{billno}"
        else:
            billno = "A1001"

        file_path = resource_path("frontend/billing.html")
        url = QUrl.fromLocalFile(file_path)
        query = f"""billno={billno}&companyname={user[1]}&username={user[2]}&email={user[3]}&mobile={user[5]}&address={user[6]}&terms={user[7].replace('&', '#')}"""
        url.setQuery(query)
        self.main_window.browser.load(url)
    
    @pyqtSlot()
    def open_customers(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM accounts")
        user = cursor.fetchone()
        file_path = resource_path("frontend/customers.html")
        url = QUrl.fromLocalFile(file_path)
        url.setQuery(f"username={user[1]}")
        self.main_window.browser.load(url)
    
    @pyqtSlot()
    def open_products(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM accounts")
        user = cursor.fetchone()
        file_path = resource_path("frontend/products.html")
        url = QUrl.fromLocalFile(file_path)
        url.setQuery(f"username={user[1]}")
        self.main_window.browser.load(url)
    
    @pyqtSlot(str)
    def open_productedit(self,id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM accounts")
        user = cursor.fetchone()

        cursor.execute("SELECT * FROM products WHERE id=?", (id))
        product = cursor.fetchone()
        
        file_path = os.path.abspath("frontend/edit_products.html")
        file_path = resource_path("frontend/edit_products.html")
        url = QUrl.fromLocalFile(file_path)
        url.setQuery(f"username={user[1]}&id={product[0]}&product_id={product[1]}&name={product[2].replace('&', '#')}&price={product[3]}&stock={product[4]}")
        self.main_window.browser.load(url)

    @pyqtSlot()
    def open_settings(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM accounts")
        user = cursor.fetchone()
        file_path = resource_path("frontend/setting.html")
        url = QUrl.fromLocalFile(file_path)
        query = f"""id={user[0]}&companyname={user[1]}&username={user[2]}&email={user[3]}&mobile={user[5]}&address={user[6]}&terms={user[7].replace('&', '#')}"""
        url.setQuery(query)
        self.main_window.browser.load(url)
    
    @pyqtSlot()
    def open_addproducts(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM accounts")
        user = cursor.fetchone()
        file_path = resource_path("frontend/addproduct.html")
        url = QUrl.fromLocalFile(file_path)
        query = f"""username={user[1]}"""
        url.setQuery(query)
        self.main_window.browser.load(url)

    @pyqtSlot(result=list)
    def get_customers(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM customers order by id desc")
        customers = cursor.fetchall()
        customers_list = [list(c) for c in customers]
        return customers_list
    
    @pyqtSlot(str, result=list)
    def get_product_by_code(self, code):
        number, letter = self.intstr(code)
        if len(number) != 3 or len(letter) != 2:
            return []
        
        pro_id = f"#{letter[0]}{number[1]}"
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM products where id=? ANd product_id=?",(number[0], pro_id))
        products = cursor.fetchall()
        products_list = [list(c) for c in products]
        return products_list
    
    @pyqtSlot(result=list)
    def get_products(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM products")
        products = cursor.fetchall()
        products_list = [list(c) for c in products]
        return products_list

    @pyqtSlot(int, str, str, str, str, str, str, str)
    def updatesetting(self, 
                      id,
                      companyname, 
                      username, 
                      email,
                      mobile,
                      address,
                      terms,
                      password
                      ):
        cursor = self.conn.cursor()
        if password:
            cursor.execute("update accounts set password=? WHERE id=?", (password, id))

        cursor.execute("update accounts set companyname=?, username=?, email=?, mobile=? ,address=?, terms=? WHERE id=?", 
                       (companyname, username, email, mobile, address, terms, id))
        self.conn.commit()

        QMessageBox.information(self.main_window, "Setting", "Account updated successfully!")
        self.open_settings()

    
    @pyqtSlot(int, str, int, int)
    def updateproducts(self, 
                      id,
                      name, 
                      price, 
                      stock
                      ):
        cursor = self.conn.cursor()
        cursor.execute("update products set name=?, amount=?, stock=? WHERE id=?", 
                       (name, price, stock, id))
        self.conn.commit()
        QMessageBox.information(self.main_window, "Product", "Product updated successfully!")
        self.open_products()

    
    @pyqtSlot(str, str, str, str, str, str, 'QVariant', 'QVariant', 'QVariant', 'QVariant', result='QVariant')
    def update_customer(self, 
                      no, 
                      name, 
                      mobile,
                      paymentmode,
                      billdate,
                      billtime,
                      items,
                      subtotal,
                      dis,
                      gtotal
                      ):
        cursor = self.conn.cursor()

        if isinstance(items, list):
            items = ",".join([f"{item[2]}-{item[1]}" for item in items])  

        if not printer_name or printer_name == "Microsoft Print to PDF":
            QMessageBox.warning(self.main_window, "Printer Error", "No printer found! Please set a printer.")
            return {"status": "error", "message": "No printer found! Please set a printer."}
        else:          
            cursor.execute("insert into customers(billno, name, mobile, paymentmode, billdate, billtime, items, subtotal, dis, gtotal) values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                        (no, name, mobile, paymentmode, billdate, billtime, items, subtotal, dis, gtotal))
            
            if isinstance(items, list):
                for item in items:
                    cursor.execute("select stock FROM products WHERE id=?",(item[0],))
                    stock = cursor.fetchone()[0]
                    stock = int(stock) - int(item[1])
                    cursor.execute("update products set stock=? WHERE id=?", (stock, item[0]))

            self.conn.commit()
            QMessageBox.information(self.main_window, "Invoice", "Invoice Generated Successfully\n\nPrinting is in Progress, please wait...")
            return {"status": "success", "message": "Invoice saved successfully"}
    
    @pyqtSlot(str, int, int)
    def addproducts(self, 
                      name, 
                      price, 
                      stock
                      ):
        cursor = self.conn.cursor()
        
        cursor.execute("select * from products order by id desc limit 1")
        last_product = cursor.fetchone()
        if last_product:
            product_id = last_product[1]
            product_id = int(product_id.replace('#PRO',"")) + 1
            product_id = f"#PRO{product_id}"
        else:
            product_id = "#PRO1"

        cursor.execute("insert into products(product_id, name, amount, stock) values(?, ?, ?, ?)", 
                       (product_id, name, price, stock))
        self.conn.commit()

        QMessageBox.information(self.main_window, "Product", "Product Added successfully!")
        self.open_products()
    
   
    @pyqtSlot(int, str)
    def delete(self,id,table):
        cursor = self.conn.cursor()
        sql = f"delete from {table} WHERE id=?"
        cursor.execute(sql, (id,))
        self.conn.commit()
        QMessageBox.information(self.main_window, "Product", "Product deleted successfully!")
        self.open_products()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        

        self.setWindowTitle("BILLING AND STOCK MANAGEMENT SYSTEM")
        self.setGeometry(100, 100, 1200, 800)
        self.setWindowIcon(QIcon("frontend/assets/images/Icon.ico"))
        # self.showFullScreen()

        self.browser = QWebEngineView()
        # file_path = os.path.abspath("frontend/index.html")
        file_path = resource_path("frontend/index.html")
        url = QUrl.fromLocalFile(file_path)
        self.browser.load(url)
        self.setCentralWidget(self.browser)

        # Connect to SQLite database
        db_path = resource_path("database.db")
        # self.conn = sqlite3.connect("database.db")
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()

        self.channel = QWebChannel()
        self.handler = BackendHandler(self, self.conn)
        self.channel.registerObject("pywebchannel", self.handler)
        self.browser.page().setWebChannel(self.channel)

    def closeEvent(self, event):
        self.conn.close()
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
