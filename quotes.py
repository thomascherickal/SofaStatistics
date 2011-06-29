import random

QUOTES = [
    (u"To understand God's thoughts we must study statistics, for these are"
     u" the measure of His purpose", "Florence Nightingale"),
    (u"Definition of Statistics: The science of producing unreliable facts "
     u"from reliable figures.", "Evan Esar"),
    (u"Torture numbers, and they'll confess to anything", "Gregg Easterbrook"),
    (u"Say you were standing with one foot in the oven and one foot in an "
     u"ice bucket.  According to the percentage people, you should be "
     u"perfectly comfortable.", "Bobby Bragan"),
    (u"Statistics can be made to prove anything - even the truth.", 
     u"Author unknown"),
    (u"He uses statistics as a drunken man uses lampposts - for support "
     u"rather than for illumination.", "Andrew Lang"),
    (u"Do not put your faith in what statistics say until you have "
     u"carefully considered what they do not say.", "William W. Watt"),
    (u"I always find that statistics are hard to swallow and impossible to "
     u"digest.  The only one I can ever remember is that if all the people "
     u"who go to sleep in church were laid end to end they would be a lot "
     u"more comfortable.", "Mrs. Robert A. Taft"),
    (u"Satan delights equally in statistics and in quoting scripture....",
     u"H.G. Wells, The Undying Fire"),
    (u"Statistics may be defined as \"a body of methods for making wise "
     u"decisions in the face of uncertainty.\"", "W.A. Wallis"),
    (u"[Science] is hard to do, unlike calculating t-statistics, which is "
     u"a simpleton's parlor game", "Ziliak & McCloskey"),
    (u"A difference is a difference only if it makes a difference.", 
     u"Common Saying"),
    (u"Statistical thinking will one day be as necessary for efficient "
     u"citizenship as the ability to read and write", u"H.G. Wells"),
    (u"Absolutely nothing should be concluded from these figures "
     u"except that no conclusion can be drawn from them.", 
     u"Joseph L. Brothers, Linux/PowerPC Project"),
    (u"Statistical significance is a phrase that every science graduate "
     u"student learns, but few comprehend.",
     u"Tom Siegfried"),
    (u"We believe that statistics can be used to support radical campaigns "
     u"for progressive social change. ... Social problems should not be "
     u"disguised by technical language.",
     u"Radical Statistics"),
    (u"Small wonder that students have trouble [learning significance testing]."
     u" They may be trying to think",
     u"W. Edwards Deming"),
    (u"Any knucklehead can calculate an average, but it takes brains to "
     u"calculate a confidence interval.", 
     u"Nate Silver"),
    (u"Statistics show that of those who contract the habit of eating, very "
     u"few survive.", u"George Bernard Shaw"),
    (u"\"Give us a copper Guv,\" said the beggar to the Treasury statistician "
     u"when he waylaid him in Parliament square. \"I haven't eaten for three days.\" "
     u"\"Ah,\" said the statistician, \"And how does that compare with the same "
     u"period last year?", u"Russell Lewis"),
    (u"It has now been proven beyond a doubt that smoking is the major cause "
     u"of statistics.", u"Unknown"),
    (u"I have always been told that old statisticians do not fade away, "
     u"but rather are \"broken down by age and sex\".", "Unknown"),
    (u"There are two kind of statistics, the kind you look up, and the "
     u"kind you make up.",  "Rex Stout (1886-1975)"),
    (u"A single death is a tragedy, a million deaths is a statistic.",
     u"Joseph Stalin (1879-1953)"),
    (u"The weaker the data available upon which to base one's conclusion, "
     u"the greater the precision which should be quoted in order to give "
     u"the data authenticity.", "Norman R. Augustine"),
    (u"Statistics means never having to say you are certain.", "Unknown"),
    (u"If there is a 50-50 chance that something can go wrong, then 9 times "
     u"out of ten it will.", u"Paul Harvey News"),
    (u"A statistician's wife had twins. He was delighted. He rang the minister "
     u"who was also delighted. \"Bring them to church on Sunday and we'll "
     u"baptize them,\" said the minister. \"No,\" replied the statistician. "
     u"\"Baptize one. We'll keep the other as a control.\"", 
     u"STATS: The Magazine For Students of Statistics"),
    (u"Reason #7 for being a statistician: You never have to be right - only close.",
     u"Unknown"),
    (u"You might be a Statistician if ... you found accountancy too exciting",
     u"Unknown"),
    ]

def get_quote():
    "Get statistics quote"
    #return QUOTES[-1] # check layout
    return random.choice(QUOTES)
