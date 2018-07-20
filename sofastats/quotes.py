import random

QUOTES = [
    ("To understand God's thoughts we must study statistics, for these are"
     " the measure of His purpose", "Florence Nightingale"),
    ("Definition of Statistics: The science of producing unreliable facts "
     "from reliable figures.", "Evan Esar"),
    ("Torture numbers, and they'll confess to anything", "Gregg Easterbrook"),
    ("Say you were standing with one foot in the oven and one foot in an "
     "ice bucket.  According to the percentage people, you should be "
     "perfectly comfortable.", "Bobby Bragan"),
    ("Statistics can be made to prove anything - even the truth.",
     "Author unknown"),
    ("He uses statistics as a drunken man uses lampposts - for support "
     "rather than for illumination.", "Andrew Lang"),
    ("Do not put your faith in what statistics say until you have "
     "carefully considered what they do not say.", "William W. Watt"),
    ("I always find that statistics are hard to swallow and impossible to "
     "digest.  The only one I can ever remember is that if all the people "
     "who go to sleep in church were laid end to end they would be a lot "
     "more comfortable.", "Mrs. Robert A. Taft"),
    ("Satan delights equally in statistics and in quoting scripture....",
     "H.G. Wells, The Undying Fire"),
    ("Statistics may be defined as \"a body of methods for making wise "
     "decisions in the face of uncertainty.\"", "W.A. Wallis"),
    ("[Science] is hard to do, unlike calculating t-statistics, which is "
     "a simpleton's parlor game", "Ziliak & McCloskey"),
    ("A difference is a difference only if it makes a difference.",
     "Common Saying"),
    ("Statistical thinking will one day be as necessary for efficient "
     "citizenship as the ability to read and write", "H.G. Wells"),
    ("Absolutely nothing should be concluded from these figures "
     "except that no conclusion can be drawn from them.",
     "Joseph L. Brothers, Linux/PowerPC Project"),
    ("Statistical significance is a phrase that every science graduate "
     "student learns, but few comprehend.",
     "Tom Siegfried"),
    ("We believe that statistics can be used to support radical campaigns "
     "for progressive social change. ... Social problems should not be "
     "disguised by technical language.",
     "Radical Statistics"),
    ("Small wonder that students have trouble [learning significance testing]."
     " They may be trying to think",
     "W. Edwards Deming"),
    ("Any knucklehead can calculate an average, but it takes brains to "
     "calculate a confidence interval.",
     "Nate Silver"),
    ("Statistics show that of those who contract the habit of eating, very "
     "few survive.", "George Bernard Shaw"),
    ("\"Give us a copper Guv,\" said the beggar to the Treasury statistician "
     "when he waylaid him in Parliament square. \"I haven't eaten for three days.\" "
     "\"Ah,\" said the statistician, \"And how does that compare with the same "
     "period last year?", "Russell Lewis"),
    ("It has now been proven beyond a doubt that smoking is the major cause "
     "of statistics.", "Unknown"),
    ("I have always been told that old statisticians do not fade away, "
     "but rather are \"broken down by age and sex\".", "Unknown"),
    ("There are two kind of statistics, the kind you look up, and the "
     "kind you make up.",  "Rex Stout (1886-1975)"),
    ("A single death is a tragedy, a million deaths is a statistic.",
     "Joseph Stalin (1879-1953)"),
    ("The weaker the data available upon which to base one's conclusion, "
     "the greater the precision which should be quoted in order to give "
     "the data authenticity.", "Norman R. Augustine"),
    ("Statistics means never having to say you are certain.", "Unknown"),
    ("If there is a 50-50 chance that something can go wrong, then 9 times "
     "out of ten it will.", "Paul Harvey News"),
    ("A statistician's wife had twins. He was delighted. He rang the minister "
     "who was also delighted. \"Bring them to church on Sunday and we'll "
     "baptize them,\" said the minister. \"No,\" replied the statistician. "
     "\"Baptize one. We'll keep the other as a control.\"",
     "STATS: The Magazine For Students of Statistics"),
    ("Reason #7 for being a statistician: You never have to be right - only close.",
     "Unknown"),
    ("You might be a Statistician if ... you found accountancy too exciting",
     "Unknown"),
    ("If you live to the age of a hundred you have it made because very few "
     "people die past the age of a hundred.", "George Burns"),
    ("If we have data, let's look at data. If all we have are opinions, let's "
     "go with mine.", "Jim Barksdale"),
    ("It is easy to lie with statistics; it is easier to lie without them.",
     "Frederick Mosteller"),
    ("There are no routine statistical questions, only questionable "
     "statistical routines.", "David Cox"),
    ("Surely, God loves the .06 nearly as much as the .05",
     "Rosnow and Rosenthal"),
    ]

def get_quote():
    "Get statistics quote"
    #return QUOTES[-1] # check layout
    return random.choice(QUOTES)
