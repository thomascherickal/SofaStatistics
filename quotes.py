import random

EN = "English"

QUOTES_EN = [
    ("To understand God's thoughts we must study statistics, for these are " + \
     "the measure of His purpose", "Florence Nightingale"),
    ("Definition of Statistics: The science of producing unreliable facts " + \
      "from reliable figures.", "Evan Esar"),
    ("Torture numbers, and they'll confess to anything", "Gregg Easterbrook"),
    ("Say you were standing with one foot in the oven and one foot in an " + \
     "ice bucket.  According to the percentage people, you should be " + \
     "perfectly comfortable.", "Bobby Bragan"),
    ("Statistics can be made to prove anything - even the truth.", 
      "Author unknown"),
    ("He uses statistics as a drunken man uses lampposts - for support " + \
     "rather than for illumination.", "Andrew Lang"),
    ("Do not put your faith in what statistics say until you have " + \
     "carefully considered what they do not say.", "William W. Watt"),
    ("I always find that statistics are hard to swallow and impossible to " + \
     "digest.  The only one I can ever remember is that if all the people " + \
     "who go to sleep in church were laid end to end they would be a lot " + \
     "more comfortable.", "Mrs. Robert A. Taft"),
    ("Satan delights equally in statistics and in quoting scripture....",
     "H.G. Wells, The Undying Fire"),
    ("Statistics may be defined as \"a body of methods for making wise " + \
     "decisions in the face of uncertainty.\"", "W.A. Wallis"),
             ]
QUOTES = {EN: QUOTES_EN}

def get_quote(lang=EN):
    "Get statistics quote"
    quotes = QUOTES[lang]
    return random.choice(quotes)