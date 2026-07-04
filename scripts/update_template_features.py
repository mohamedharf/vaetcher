import os

filepath = r"c:\Users\PC HOME\OneDrive\Desktop\hadramout_events\hadramout_events_final\hadramout_events\templates\custom_admin\vendor_settlements.html"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update export button to trigger JS export
old_export_btn = """            <button class="btn btn-secondary" style="border-radius: var(--radius-full);">
                <i class="fa-solid fa-file-export"></i> تصدير إكسيل
            </button>"""

new_export_btn = """            <button class="btn btn-secondary" style="border-radius: var(--radius-full);" onclick="exportActiveTabToCSV()">
                <i class="fa-solid fa-file-export"></i> تصدير إكسيل
            </button>"""

content = content.replace(old_export_btn, new_export_btn)

# 2. Add search bar to Vendors Tab
old_vendors_header = """            <div class="flex-row justify-between items-center mb-md">
                <h2 class="headline-sm" style="margin: 0;">الموردين المستحقين</h2>
            </div>"""

new_vendors_header = """            <div class="flex-row justify-between items-center mb-md gap-md">
                <h2 class="headline-sm" style="margin: 0;">الموردين المستحقين</h2>
                <div style="position: relative; width: 300px;">
                    <input type="text" id="vendorSearchInput" placeholder="البحث باسم المورد..." 
                           style="width: 100%; padding: 8px 12px 8px 35px; border: 1px solid var(--outline-variant); border-radius: var(--radius-md);"
                           onkeyup="filterVendorsList()">
                    <i class="fa-solid fa-magnifying-glass" style="position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: var(--on-surface-variant); opacity: 0.5;"></i>
                </div>
            </div>"""

content = content.replace(old_vendors_header, new_vendors_header)

# 3. Add search bar to Companies Tab
old_companies_header = """            <div class="flex-row justify-between items-center mb-md">
                <h2 class="headline-sm" style="margin: 0;">تسويات الشركات الدوائية</h2>
                <button class="btn btn-primary" onclick="openSettlementModal('company_settlement', '', '', 0, 0)">
                    <i class="fa-solid fa-plus"></i> تسوية شركة جديدة
                </button>
            </div>"""

new_companies_header = """            <div class="flex-row justify-between items-center mb-md gap-md">
                <h2 class="headline-sm" style="margin: 0;">تسويات الشركات الدوائية</h2>
                <div class="flex-row items-center gap-md">
                    <div style="position: relative; width: 250px;">
                        <input type="text" id="companySearchInput" placeholder="البحث باسم الشركة..." 
                               style="width: 100%; padding: 8px 12px 8px 35px; border: 1px solid var(--outline-variant); border-radius: var(--radius-md);"
                               onkeyup="filterCompaniesTable()">
                        <i class="fa-solid fa-magnifying-glass" style="position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: var(--on-surface-variant); opacity: 0.5;"></i>
                    </div>
                    <button class="btn btn-primary" onclick="openSettlementModal('company_settlement', '', '', 0, 0)">
                        <i class="fa-solid fa-plus"></i> تسوية شركة جديدة
                    </button>
                </div>
            </div>"""

content = content.replace(old_companies_header, new_companies_header)

# 4. Add search bar to Delegates Tab
old_delegates_header = """            <div class="flex-row justify-between items-center mb-md">
                <h2 class="headline-sm" style="margin: 0;">تسويات المناديب</h2>
                <button class="btn btn-primary" onclick="openSettlementModal('delegate_settlement', '', '', 0, 0)">
                    <i class="fa-solid fa-plus"></i> تسوية مندوب جديدة
                </button>
            </div>"""

new_delegates_header = """            <div class="flex-row justify-between items-center mb-md gap-md">
                <h2 class="headline-sm" style="margin: 0;">تسويات المناديب</h2>
                <div class="flex-row items-center gap-md">
                    <div style="position: relative; width: 250px;">
                        <input type="text" id="delegateSearchInput" placeholder="البحث باسم المندوب..." 
                               style="width: 100%; padding: 8px 12px 8px 35px; border: 1px solid var(--outline-variant); border-radius: var(--radius-md);"
                               onkeyup="filterDelegatesTable()">
                        <i class="fa-solid fa-magnifying-glass" style="position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: var(--on-surface-variant); opacity: 0.5;"></i>
                    </div>
                    <button class="btn btn-primary" onclick="openSettlementModal('delegate_settlement', '', '', 0, 0)">
                        <i class="fa-solid fa-plus"></i> تسوية مندوب جديدة
                    </button>
                </div>
            </div>"""

content = content.replace(old_delegates_header, new_delegates_header)

# 5. Add JS functions for filter and export
old_js_block = """        function closeSettlementModal() {
            document.getElementById('settlementOverlay').classList.remove('active');
        }"""

new_js_block = """        function closeSettlementModal() {
            document.getElementById('settlementOverlay').classList.remove('active');
        }

        // Live Search Filter for Vendors List
        function filterVendorsList() {
            const query = document.getElementById('vendorSearchInput').value.toLowerCase();
            const rows = document.querySelectorAll('#tab-vendors .list-row');
            rows.forEach(row => {
                const name = row.querySelector('.title-md').innerText.toLowerCase();
                const code = row.querySelector('.label-md').innerText.toLowerCase();
                if (name.includes(query) || code.includes(query)) {
                    row.style.display = 'flex';
                } else {
                    row.style.display = 'none';
                }
            });
        }

        // Live Search Filter for Companies Table
        function filterCompaniesTable() {
            const query = document.getElementById('companySearchInput').value.toLowerCase();
            const rows = document.querySelectorAll('#tab-companies table tr');
            rows.forEach((row, index) => {
                if (index === 0) return; // skip header
                const text = row.innerText.toLowerCase();
                if (text.includes(query)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        }

        // Live Search Filter for Delegates Table
        function filterDelegatesTable() {
            const query = document.getElementById('delegateSearchInput').value.toLowerCase();
            const rows = document.querySelectorAll('#tab-delegates table tr');
            rows.forEach((row, index) => {
                if (index === 0) return; // skip header
                const text = row.innerText.toLowerCase();
                if (text.includes(query)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        }

        // Client-side CSV Exporter
        function exportActiveTabToCSV() {
            const activeTab = localStorage.getItem('activeSettlementsTab') || 'vendors';
            let table = null;
            let filename = '';
            
            if (activeTab === 'vendors') {
                table = document.querySelector('#tab-vendors table');
                filename = 'vendor_settlements.csv';
            } else if (activeTab === 'companies') {
                table = document.querySelector('#tab-companies table');
                filename = 'company_settlements.csv';
            } else if (activeTab === 'delegates') {
                table = document.querySelector('#tab-delegates table');
                filename = 'delegate_settlements.csv';
            }
            
            if (!table) return;
            
            let csv = [];
            const rows = table.querySelectorAll('tr');
            for (let i = 0; i < rows.length; i++) {
                const row = [], cols = rows[i].querySelectorAll('td, th');
                for (let j = 0; j < cols.length; j++) {
                    if (j === cols.length - 1 && i > 0) continue; // skip image column
                    let text = cols[j].innerText.trim().replace(/"/g, '""');
                    row.push('"' + text + '"');
                }
                csv.push(row.join(','));
            }
            
            const csvContent = "data:text/csv;charset=utf-8,\\uFEFF" + csv.join("\\n");
            const encodedUri = encodeURI(csvContent);
            const link = document.createElement("a");
            link.setAttribute("href", encodedUri);
            link.setAttribute("download", filename);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }"""

content = content.replace(old_js_block, new_js_block)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("Updated template with advanced features successfully.")
