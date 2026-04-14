# VHS tape for SkiLens demo GIF
# Render with: vhs scripts/demo.tape
# Produces: docs/demo.gif

Output docs/demo.gif

# Works on Linux/macOS out of the box.
# On Windows, VHS + ttyd + MSYS bash is flaky — use the SVG export instead:
#   python -m scripts.demo --svg docs/demo.svg

Set FontSize 14
Set Width 1000
Set Height 780
Set Padding 20
Set Theme "Dracula"
Set TypingSpeed 60ms
Set PlaybackSpeed 1.0

Type "skillens "
Sleep 200ms
Type `"https://www.coursera.org/learn/machine-learning"`
Sleep 400ms
Enter
Sleep 600ms

Hide
Type "clear && PYTHONIOENCODING=utf-8 python -X utf8 -m scripts.demo"
Enter
Sleep 100ms
Show

Sleep 5s
