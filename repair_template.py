
with open('templates/custom_admin/doctors_directory.html', 'rb') as f:
    content = f.read()

# Finding the specific broken point
bad_marker = b'\xd9\x83\xd9\x84\xd9\x85\xd8\xa9 \xd8\xa7\xd9\x84\xd9\x85\xd8\xb1\xd9\x88\xd8'
# Replace it with the correct full block
restoration = """كلمة المرور المؤقتة</label>
                    <input type="password" name="password" class="input-premium" style="background: var(--surface-container-low); padding: 10px; width: 100%;" required>
                </div>

                <button type="submit" class="btn btn-primary" style="margin-top: 10px; width: 100%;">
                    <i class="fa-solid fa-user-plus"></i> اعتماد وإضافة الطبيب
                </button>
            </form>
        </div>
    </div>""".encode('utf-8')

if bad_marker in content:
    new_content = content.replace(bad_marker, restoration)
    with open('templates/custom_admin/doctors_directory.html', 'wb') as f:
        f.write(new_content)
    print("Repair successful")
else:
    print("Marker not found")
