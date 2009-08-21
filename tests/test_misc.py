from nose.tools import assert_equal
from .output import _strip_html
from .output import _strip_script
from my_globals import SCRIPT_END

def test_strip_html():
    tests = [("<body>Freddy</body>", "Freddy"), 
             ("<body>Freddy</body>Teddy</body>", "Freddy"),
             ("<body>Freddy", "Freddy"),
             ]
    for test in tests:
        assert_equal(_strip_html(test[0]), test[1])

def test_strip_script():
    tests = [("\nchunky chicken%s\nxzmxnzmxnz" % SCRIPT_END, "\nchunky chicken")]
    for test in tests:
        assert_equal(_strip_script(test[0]), test[1])