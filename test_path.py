from pathlib import Path
p = Path("/home/likelipop/Project/ReadandQues/ReadAndQues/articles/views.py")
print("1 parent:", p.parent)
print("2 parents:", p.parent.parent)
print("3 parents:", p.parent.parent.parent)
print("4 parents:", p.parent.parent.parent.parent)
