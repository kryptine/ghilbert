# Copyright 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This is the main AppEngine content handler for serving Ghilbert.

import cgi
import urllib
import logging
import StringIO
import verify
from time import gmtime, strftime
import re

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db

from django.utils import simplejson

class Goal(db.Model):
    name = db.StringProperty()
    value = db.IntegerProperty()
    next = db.StringProperty()
    ghilbert = db.StringProperty()
    html = db.TextProperty()
    # TODO: which interfaces are required; which goals are required; branch points
    
#TODO:hack
def get_goal(name):
    goal = Goal.get_or_insert(key_name=name)
    if (goal.name is None):
        goal.name = name
        if (name == "idd"):
            goal.next = "id"
            goal.value = 1
            goal.html = "(&#x2192; A (&#x2192; B B))"
            goal.ghilbert = "() () (-> A (-> B B))"
            goal.put()
        elif (name == "id"):
            goal.next = "imim2"
            goal.value = 1
            goal.html = "(&#x2192; A A)"
            goal.ghilbert = "() () (-> A A)"
            goal.put()
        elif (name == "imim2"):
            goal.next = "imim1"
            goal.value = 1
            goal.html = "(&#x2192; (&#x2192; A B) (&#x2192; (&#x2192; C A) (&#x2192; C B))))"
            goal.ghilbert = "() () (-> (-> A B) (-> (-> C A) (-> C B)))" 
            goal.put()
        elif (name == "imim1"):
            goal.next = "assertion"
            goal.value = 1
            goal.html = "(&#x2192; (&#x2192; A B) (&#x2192; (&#x2192; B C) (&#x2192; A C))))"
            goal.ghilbert = "() () (-> (-> A B) (-> (-> B C) (-> A C)))" 
            goal.put()
        elif (name == "assertion"):
            goal.next = "tie"
            goal.value = 1
            goal.html = "(&#x2192; A (&#x2192; (&#x2192; A B) B)))"
            goal.ghilbert = "() () (-> A (-> (-> A B) B))" 
            goal.put()
        elif (name == "tie"):
            goal.next = "con12"
            goal.value = 1
            goal.html = "(&#x2192; (&#x2192; (&#x2192; A A) B) B)"
            goal.ghilbert = "() () (-> (-> (-> A A) B) B)" 
            goal.put()
        elif (name == "con12"):
            goal.next = "contraction"
            goal.value = 1
            goal.html = "(&#x2192; (&#x2192; A (&#x2192; B C)) (&#x2192; B (&#x2192; A C)))"
            goal.ghilbert = "() () (-> (-> A (-> B C)) (-> B (-> A C)))" 
            goal.put()
        elif (name == "contraction"):
            goal.next = "fie"
            goal.value = 1
            goal.html = "(&#x2192; (&#x2192; A (&#x2192; A B)) (&#x2192; A B))"
            goal.ghilbert = "() () (-> (-> A (-> A B)) (-> A B))"
            goal.put()
        elif (name == "fie"):
            goal.next = "notnot2"
            goal.value = 1
            goal.html = "(&#x2192; ((&#x00ac; A) (&#x2192; A B)))"
            goal.ghilbert = "() () (-> (-. A) (-> A B))"
            goal.put()
        elif (name == "notnot1"):
            goal.next = "con3"
            goal.value = 1
            goal.html = "(&#x2192; (A (&#x00ac; (&#x00ac; A)))"
            goal.ghilbert = "() () (-> A (-. (-. A)))"
            goal.put()
        elif (name == "notnot2"):
            goal.next = "notnot1"
            goal.value = 1
            goal.html = "(&#x2192; (&#x00ac; (&#x00ac; A)) A)"
            goal.ghilbert = "() () (-> (-. (-. A)) A)"
            goal.put()
        elif (name == "con3"):
            goal.next = "nimp2"
            goal.value = 1
            goal.html = "(&#x2192;  (&#x2192; A B)  (&#x2192; (&#x00ac; B) (&#x00ac; A)))"
            goal.ghilbert = "() () (-> (-> A B) (-> (-. B) (-. A)))"
            goal.put()
        elif (name == "nimp2"):
            goal.next = "nimp1"
            goal.value = 1
            goal.html = "(&#x2192; (&#x00ac; (&#x2192; A B)) (&#x00ac; B))"
            goal.ghilbert = "() () (-> (-. (-> A B)) (-. B))"
            goal.put()
        elif (name == "nimp1"):
            goal.next = "mth8"
            goal.value = 1
            goal.html = "(&#x2192; (&#x00ac; (&#x2192; A B)) A)"
            goal.ghilbert = "() () (-> (-. (-> A B)) A)"
            goal.put()
        elif (name == "mth8"):
            goal.next = "df-and-just"
            goal.value = 1
            goal.html = "(&#x2192; A (&#x2192; (&#x00ac; B) (&#x00ac; (&#x2192; A B))))"
            goal.ghilbert = "() () (-> A (-> (-. B) (-. (-> A B))))"
            goal.put()
        elif (name == "df-and-just"):
            goal.next = "PICKUP(df-bi)"
            goal.value = 1
            goal.html = "(&#x00ac; (&#x2192; (&#x2192; (&#x00ac; (&#x2192; A (&#x00ac; B)))) (&#x00ac; (&#x2192; A (&#x00ac; B)))) (&#x00ac; (&#x2192; (&#x00ac; (&#x2192; C (&#x00ac; D))) (&#x00ac; (&#x2192; C (&#x00ac; D))))))"
            goal.ghilbert = "() () (-. (-> (-> (-. (-> A (-. B)))) (-. (-> A (-. B)))) (-. (-> (-. (-> C (-. D))) (-. (-> C (-. D))))))"
            goal.put()
        else:
            goal.html = "Sorry, goal '%s' isn't defined yet.  No one thought you'd make it this far!" % name
    return goal
#TODO: OO
def check_goal(player, proof, thmName, stream):
    goal = get_goal(player.goal)
    if (goal.ghilbert is None):
        return False
    pattern = "thm \([^)]* " + goal.ghilbert.replace("(","\(").replace(")","\)")
    if re.match(pattern, proof):
        player.score += goal.value
        if (player.goal == "contraction"): #TODO:data driven
            send_to_CorePropCal(player, stream)
        elif (player.goal == "df-and-just"):
            # TODO: PICKUP: add defthm, parameterize tips, inform user of new thm
            unlock_and(player, thmName, stream)
        else:
            stream.write("GHT.Tip.set('achieved');\n")
        player.goal = goal.next

        return True
    stream.write("/*\n MATCH: " + pattern + " #### AGAINST: " + proof + "\n*/\n")
    return False

def unlock_and(player, stream, thmName, dfandname):
    stream.write("GHT.Tip.set('andUnlocked');\n")
    newJs ="""
// And
GHT.Operators["/\\"] = new Operator("/\\","\u2227","wff",["wff","wff"],[1,1]);
GHT.Thms["Conjoin"] =  T(O("-."),T(O("->"),T(O("->"),T(O("/\\"),TV("wff", -360),TV("wff", -361)),T(O("-."),T(O("->"),TV("wff", -360),TV("wff", -361)))),T(O("-."),T(O("->"),T(O("-."),T(O("->"),TV("wff", -360),TV("wff", -361))),T(O("/\\"),TV("wff", -360),TV("wff", -361))))));
GHT.ArrowScheme["/\\"] = ["anim1i", "anim2i"];
"""
    stream.write(newJs);
    player.setupJs += newJs;
    player.goal = "df-and-1"
    player.ghilbertText += """
defthm (Conjoin wff (/\ A B) () ()
          (-. (-> (-> (/\ A B) (-. (-> A (-. B))))
                  (-. (-> (-. (-> A (-. B))) (/\ A B)))))
     (-. (-> A (-. B)))  (-. (-> A (-. B)))  %s
)
#TODO: anim{1,2}i
""" % thmName


def send_to_CorePropCal(player, stream):
    player.location = "Outer Procal"
    stream.write("GHT.Tip.set('negUnlocked');\n")
    newJs ="""
// CorePropCal
GHT.Operators["-."] = new Operator("-.","\u00ac","wff",["wff"],[-1]);
GHT.Thms["Transpose"] = T(O("->"),T(O("->"),T(O("-."),TV("wff", -560)),T(O("-."),TV("wff", -571))),T(O("->"),TV("wff", -571),TV("wff", -560)));
GHT.ArrowScheme["-."] = ["con3i"];
"""
    stream.write(newJs);
    player.goal = "fie"
    player.setupJs += newJs;
    player.ghilbertText += """
import (COREPROPCAL CorePropCal (POSPROPCAL) "")
"""
    
class Player(db.Model):
    name = db.StringProperty()
    lastSeen = db.DateTimeProperty(auto_now=True)
    score = db.IntegerProperty()
    location = db.StringProperty()
    goal = db.StringProperty()
    # JS that sets up the tree-proof environment: operators, theorems, arrow schemes
    setupJs = db.TextProperty()
    # Keys into the GhilbertInterface table; points to which interfaces the user has unlocked.
    ghilbertInterfaces = db.StringListProperty()
    # ghilbert-parsable text for the player's theorems
    ghilbertText = db.TextProperty()
    # Log of all actions
    log = db.TextProperty()
    # Javascript for updating the UI to reflect this object's current state
    def update_js(self):
        dict = {};
        for k in ("score", "location", "goal", "name"):
            dict[k] = getattr(self,k);
        dict["goal"] = get_goal(dict["goal"]).html
        return "\nGHT.updateUi('player',%s);\n" % simplejson.dumps(dict)
        
class StatusJs(webapp.RequestHandler):
    def get(self, playerName):
        player = Player.get_or_insert(key_name=playerName)
        tip = '"Welcome back."';
        if (player.location is None):
            player.score = 0
            player.location = "Inner Procal"
            player.goal="idd"
            player.name = playerName
            player.log = "### Created " + strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime())
            player.setupJs = """
GHT.Operators = {};
GHT.Thms = {};
GHT.ArrowScheme = {};
GHT.DisabledOptions = {};
GHT.Operators["->"] = new Operator("->","\u2192","wff",["wff","wff"],[-1,1]);
GHT.Thms["Simplify"] = T(O("->"),TV("wff", -1),T(O("->"),TV("wff", -2),TV("wff", -1)));
GHT.Thms["Distribute"] = T(O("->"),T(O("->"),TV("wff", -1),T(O("->"),TV("wff", -2),TV("wff", -3))),T(O("->"),T(O("->"),TV("wff", -1),TV("wff", -2)),T(O("->"),TV("wff", -1),TV("wff", -3))));
GHT.ArrowScheme["mp"] = ["ax-mp", "ax-mp"]; //TODO: what does this second ax-mp really mean? why does that work?
GHT.ArrowScheme["->"] = ["imim1i", "imim2i"];
GHT.DisabledOptions.generify = 1;
GHT.DisabledOptions.equivalents = 1;
GHT.DisabledOptions.initials = 1;
GHT.DisabledOptions["term substitute"] = 1;
GHT.DisabledOptions.terminals = 1;
GHT.setProof((new GHT.ProofFactory()).newProof("Simplify"));

"""
            player.ghilbertInterfaces = ["PosPropCal"]
            player.ghilbertText = """
import (POSPROPCAL PosPropCal () "")
tvar (wff A B C D E F G H)
"""

            tip = '"Welcome!  I see you\'re new here.  Feel free to click around and explore.  You can\'t mess up."'
            player.put()
        self.response.out.write(player.setupJs);
        self.response.out.write('GHT.Tip.set("welcome", %s);\n' % tip);
        self.response.out.write(player.update_js());


class SaveHandler(webapp.RequestHandler):
    def post(self):
        # Note, the following line gets the un-url-encoded name.
        playerName = self.request.get('playerName')
        player = Player.get_by_key_name(playerName)
        if (player is None):
            self.response.out.write("GHT.Tip.set('You need a name if you want your saves to last!');")
        else:
            pass
        interfaces = {'PosPropCal':"""
# positive propositional calculus
kind (wff)
tvar (wff A B C)
term (wff (-> A B))
stmt (Simplify () () (-> A (-> B A)))
stmt (Distribute () () (-> (-> A (-> B C)) (-> (-> A B) (-> A C))))
stmt (ax-mp () (A (-> A B)) B)
#TODO: provable from above... reduce the interface?
stmt (imim1i () ((-> A B)) (-> (-> B C) (-> A C)))
stmt (imim2i () ((-> A B)) (-> (-> C A) (-> C B)))
""",
                      'CorePropCal':"""
param (POSPROPCAL PosPropCal () "")
tvar (wff A B C)
term (wff (-. A))
stmt (Transpose () () (-> (-> (-. A) (-. B)) (-> B A)))
#TODO: provable from above... reduce the interface?
stmt (con3i () ((-> A B)) (-> (-. B) (-. A)))
"""
                      }
        newProof = self.request.get('proof')
        thmName = self.request.get('thmName')
        proofText = player.ghilbertText + "\n" + newProof + "\n"
        output = StringIO.StringIO();
        output.write("Verifying: \n===\n%s\n===\n" % proofText);
        interfaces["-"] = proofText;
        urlctx = verify.DictionaryCtx(interfaces)
        ctx = verify.VerifyCtx(urlctx, verify.run, False)
        ctx.run(urlctx, '-', ctx, output)
        if ctx.error_count > 0:
            self.response.out.write("GHT.Tip.set('saveError', 'Cannot save!');\n/*\n%s\n*/" % output.getvalue())
        else:
            player.ghilbertText = proofText;
            player.log += "\n# %s\n%s\n" % (strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime()),
                                            self.request.get('log'))
            player.setupJs += "GHT.Thms['%s'] = %s;\n" % (thmName, self.request.get('source'))
            if (check_goal(player, newProof, thmName, self.response.out)):
                self.response.out.write(player.update_js())
            else:
                self.response.out.write("GHT.Tip.set('saved');\n")
            player.put()

application = webapp.WSGIApplication(
                                     [('/tree/status/(.*)', StatusJs),
                                      ('/tree/save', SaveHandler),
                                      ],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
