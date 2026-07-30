import os

base_dir = '/home/likelipop/Project/ReadandQues/ReadAndQues/articles/templates/articles'
detail_path = os.path.join(base_dir, 'detail.html')
includes_dir = os.path.join(base_dir, 'includes')

with open(detail_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

def write_include(filename, start, end):
    with open(os.path.join(includes_dir, filename), 'w', encoding='utf-8') as f:
        f.writelines(lines[start-1:end])

# _styles.html (9-66)
write_include('_styles.html', 9, 66)

# _toolbar.html (94-101)
write_include('_toolbar.html', 94, 101)

# _article_content.html (103-113)
write_include('_article_content.html', 103, 113)

# _quiz_sidebar.html (115-245)
write_include('_quiz_sidebar.html', 115, 245)

# _scripts.html (248 to end - 2 lines for </body></html>)
end_script = len(lines)
for i in range(len(lines)-1, 0, -1):
    if '</body>' in lines[i]:
        end_script = i
        break
write_include('_scripts.html', 248, end_script)

# Reconstruct detail.html
new_lines = []
new_lines.extend(lines[0:8]) # lines 1-8
new_lines.append('    {% include "articles/includes/_styles.html" %}\n')
new_lines.extend(lines[66:93]) # lines 67-93
new_lines.append('        {% include "articles/includes/_toolbar.html" %}\n')
new_lines.append('        {% include "articles/includes/_article_content.html" %}\n')
new_lines.append('        {% include "articles/includes/_quiz_sidebar.html" %}\n')
new_lines.extend(lines[245:247]) # lines 246-247 </main>
new_lines.append('    {% include "articles/includes/_scripts.html" %}\n')
new_lines.extend(lines[end_script:])

with open(detail_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print("Splitting complete.")
