import sqlite3

conn = sqlite3.connect('flowcore.db')
cur = conn.cursor()

BUSINESS_ID = 'e216b183-8c91-4a56-b819-50ebfb3f8a45'
NEW_NUMBER = '+919652778472'

cur.execute(
    "UPDATE businesses SET whatsapp_number = ? WHERE id = ?",
    (NEW_NUMBER, BUSINESS_ID)
)
conn.commit()
print(f"Updated rows: {cur.rowcount}")

cur.execute(
    "SELECT id, name, whatsapp_number FROM businesses WHERE id = ?",
    (BUSINESS_ID,)
)
row = cur.fetchone()
print(f"Business: {row[1]}")
print(f"WhatsApp: {row[2]}")
conn.close()
