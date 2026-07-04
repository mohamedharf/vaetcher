
import os

file_path = 'core/views.py'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if 'elif len(new_password) < 6:' in line and 'class' not in line:
        new_lines.append(line)
        new_lines.append('                messages.error(request, "كلمة المرور يجب أن تكون 6 أحرف على الأقل.")\n')
        new_lines.append('            else:\n')
        new_lines.append('                request.user.set_password(new_password)\n')
        new_lines.append('                request.user.save()\n')
        new_lines.append('                from django.contrib.auth import update_session_auth_hash\n')
        new_lines.append('                update_session_auth_hash(request, request.user)\n')
        new_lines.append('                messages.success(request, "تم تغيير كلمة المرور بنجاح.")\n')
        new_lines.append('        \n')
        new_lines.append('        return redirect("custom_doctor_settings")\n')
        new_lines.append('\n')
    else:
        new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
