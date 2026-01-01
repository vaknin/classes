from bs4 import BeautifulSoup

with open('output/html/page_001.html', 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')
table = soup.find('table', {'id': 'ContentPlaceHolder1_gvData'})

if table:
    rows = table.find_all('tr')
    # Print header
    print("Header:")
    print(rows[0])
    # Print first data row
    if len(rows) > 1:
        print("\nFirst Row:")
        print(rows[1])
else:
    print("Table not found")
