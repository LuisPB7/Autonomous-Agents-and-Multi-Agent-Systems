import time, random, math
import numpy as np
from operator import attrgetter
import operator
from collections import Counter

global werewolves, villagers, seers, doctors, all_villagers

# ----------------- Defining our population ------------ #
print("Welcome to Werewolf!")

n_villagers = eval(input("How many villagers do you want?: "))
n_werewolves = eval(input("How many werewolves do you want?: "))
n_seers = math.ceil(0.1 * n_villagers)
n_doctors = math.ceil(0.1 * n_villagers)
werewolves = []
villagers = []
seers = []
doctors = []
all_villagers = []

# ------------------ Useful variables ------------------- #

last_dead_voting = None #Last villager who died in the villager voting
last_dead_werewolves = None #Last villager who died killed by the werewolves
current_voting = {}
total_voting = {v:[] for v in all_villagers} # Villager:Villager voted
current_werewolf_voting = []
villagers_healed_by_the_doctor = []
game_mode = None #Game Mode
player_name = ""
player_type = ""
dead_player = False
deadLastVote = None
deadVoteList = []
surviving_villagers = []
surviving_werewolves = []

def fill_initial_belief(v):
    global all_villagers
    d = {}
    for villager in all_villagers:
        if villager.getName() != v.getName():
            d[villager.getName()] = [1/(n_villagers+n_werewolves-1), 1/(n_villagers+n_werewolves-1), 1/(n_villagers+n_werewolves-1), 1/(n_villagers+n_werewolves-1)]
    return d

def delete_dead_beliefs(deadGuy):
    global all_villagers
    for villager in all_villagers:
        del villager.getBelief()[deadGuy.getName()]
        try:
            normalize_belief(villager, 0)
        except: pass
    

#----------------------- Role classes --------------------- #

class Villager:
    
    def __init__(self, name):
        self._name = name
        self._intelligence = random.randint(1,100)
        self._respect = random.randint(1,100)
        self._laziness = random.randint(1,100)
        self._faith = random.randint(1,100)
        self._stubborness = random.randint(1,100)
        self._fear = random.randint(1,100)
        self._veracity = random.randint(1,100)
        self._belief = {} #fill_initial_belief(self) # belief = [Jogador2:(1/4, 1/4, 1/4, 1/4), Jogador3:(...)
        self._lastStrategy = None
        self._Q = {random_strategy:0 , dead_last_vote:0 , dead_most_voted:0 , less_respected:0 , ask_someone:0}
    
    def getName(self):
        return self._name
    
    def setName(self, name):
        self._name = name
        
    def getQ(self):
        return self._Q
    
    def setQ(self, Q):
        self._Q = Q
    
    def getBelief(self):
        return self._belief

    def setBelief(self, belief):
        self._belief = belief
    
    def getRespect(self):
        return self._respect
    
    
    
    def updateQ(self, dead, reward):
        try:
            self._Q[self._lastStrategy] = self._Q[self._lastStrategy] + (self._intelligence/100) * (reward + 0.9 * max(self._Q.values()) - self._Q[self._lastStrategy])
        except: pass
    
    def advise(self, other):
        if self._name != player_name:
            lie_probability = [self._veracity/100, 1-(self._veracity/100)]
            suspect = getVillager(max(self._belief, key=self._belief.get))
            try:
                lie = np.random.choice(list(set(all_villagers)-set([self])-set([suspect])-set([other])))
            except:
                return other
            possible_answers = [suspect, lie]
            answer = np.random.choice(possible_answers, p=lie_probability)
            if other._name == player_name:
                print(self._name + " advised you to vote for " + answer.getName())
            return answer
        else:
            advice = input(other.getName() + " asked for your advice regarding who to vote. What villager number will you advise?\n")
            return getVillager("Villager"+advice)
        
    def vote(self): #De acordo com os beliefs sobre quem e o lobisomem, escolher uma vitima para votar
        global current_voting, all_villagers, total_voting
        probabilities = []
        list_to_choose = list(set(all_villagers)-set([self]))
        #Ir buscar um lobisomem com probabilidade dos beliefs
        if(self.getName() == player_name):
            print("Select the number of the villager you think it's a werewolf from this list: \n")
            for villager in list_to_choose:
                print(villager.getName())
            chosenVillagerName = "Villager" + input(": ")
            for vil in list_to_choose:
                if(vil.getName() == chosenVillagerName):
                    chosenVillager = vil        
        else:
            for villager in list_to_choose:
                probabilities = probabilities + [self._belief[villager.getName()][0]]
            probabilities = [i/sum(probabilities) for i in probabilities]
            chosenVillager = np.random.choice(list_to_choose, p=probabilities)
        current_voting[self] = chosenVillager
        total_voting[self] = total_voting[self] + [chosenVillager]
        print(self._name + " voted for " + chosenVillager.getName())
        
    def think(self): #Atualizar os beliefs sobre quem e o lobisomem
        global villager_voting_strategies
        if self._name == player_name:
            choice = input("What do you want to do? Vote(V) or Ask for Advice(A) ? ")
            if choice == "V":
                return
            elif choice == "A":
                print("Select the number of the villager you want to ask for advice from this list: \n")
                for villager in list(set(all_villagers)-set([self])):
                    print(villager.getName())
                chosenVillagerName = "Villager" + input(": ")
                vil = getVillager(chosenVillagerName)
                adv = vil.advise(self)
                print(vil.getName() + " advised you to vote for " + adv.getName() + "\n")
                
        else:
            probabilities = [0.6*self._laziness, 0.8*(100-self._intelligence), 0.8*self._intelligence, 0.8*self._respect, 0.8*self._faith]
            probabilities = [p/sum(probabilities) for p in probabilities] #Normalize
            strategy = np.random.choice(villager_voting_strategies, p=probabilities)
            bestKnowStrategy = max(self._Q, key=self._Q.get)
            choices = [strategy, bestKnowStrategy]
            probabilities = [self._stubborness/100, 1-(self._stubborness/100)]
            strategy = np.random.choice(choices, p=probabilities)
            strategy(self)
            self._lastStrategy = strategy
        
class Werewolf(Villager):
    
    def __init__(self, name):
        super().__init__(name)
        self._QKill = {kill_seer:0, kill_doctor:0, kill_randomly:0, kill_most_respected:0, kill_who_not_voted_me:0, kill_who_voted_me:0, kill_who_voted_me_most:0}
        self._lastKillingStrategy = None
    
    def kill(self):
        print("RIP someone")
        
    def updateQKill(self, dead, reward):
        try:
            self._QKill[self._lastKillingStrategy] = self._QKill[self._lastKillingStrategy] + (self._intelligence/100) * (reward + 0.9 * max(self._QKill.values()) - self._QKill[self._lastKillingStrategy])
        except: pass    
        
    def advise(self, other):
        if self._name != player_name:
            return np.random.choice(list(set(all_villagers)-set(werewolves)-set([other])))
        else:
            advice = input(other.getName() + " asked for your advice regarding who to vote. What villager number will you advise?\n")
            return getVillager("Villager"+advice)            
        
    def think(self):
        None
    
    def getQKill(self):
        return self._QKill
    
    def setQKill(self, Q):
        self._QKill = Q
    
    def vote(self):
        global villager_voting_strategies, current_voting, total_voting
        if(self.getName() == player_name):
            print("Select the number of the villager you want to vote from this list: \n")
            for villager in list(set(all_villagers)-set(werewolves)):
                print(villager.getName())
            chosenVillagerName = "Villager" + input(": ")
            victim = getVillager(chosenVillagerName)
        else:
            probabilities = [0.6*self._laziness, 0.8*(100-self._intelligence), 0.8*self._intelligence, 0.8*self._respect, 0.8*self._faith]
            probabilities = [p/sum(probabilities) for p in probabilities] #Normalize
            strategy = np.random.choice(villager_voting_strategies, p=probabilities)
            bestKnowStrategy = max(self._Q, key=self._Q.get)
            choices = [strategy, bestKnowStrategy]
            probabilities = [self._stubborness/100, 1-(self._stubborness/100)]
            strategy = np.random.choice(choices, p=probabilities)        
            victim = strategy(self)
            self._lastStrategy = strategy
        if victim == None:
            victim = random_strategy(self)
        current_voting[self] = victim
        total_voting[self] = total_voting[self] + [victim]
        print(self._name + " voted for " + victim.getName())
        
    def voteKill(self):
        global werewolf_killing_strategies, current_voting, total_voting, current_werewolf_voting, player_name, all_villagers
        if(self.getName() == player_name):
            print("Select the number of the villager you wish to kill from this list:\n")
            for villager in list(set(all_villagers)-set(werewolves)):
                print(villager.getName())
            chosenVillagerName = "Villager" + input(": ")
            victim = getVillager(chosenVillagerName)
        else:
            probabilities = [0.8*self._intelligence, 0.5*(0.5*self._intelligence+0.5*self._fear), 0.6*self._laziness, 0.8*self._respect, 0.8*(100-self._intelligence), 0.8*self._fear,0.8*(100-self._fear)]
            probabilities = [p/sum(probabilities) for p in probabilities] #Normalize
            strategy = np.random.choice(werewolf_killing_strategies, p=probabilities)
            bestKnowStrategy = max(self._Q, key=self._Q.get)
            choices = [strategy, bestKnowStrategy]
            probabilities = [self._stubborness/100, 1-(self._stubborness/100)]
            strategy = np.random.choice(choices, p=probabilities)
            self._lastKillingStrategy = strategy
            victim = strategy(self)
        current_werewolf_voting = current_werewolf_voting + [victim]
    
    def thinkKill(self):
        print("Thinking about who to kill")
        
class Seer(Villager):
    
    def __init__(self, name):
        super().__init__(name)
        self._knownInnocents = [self]
        self._knownWerewolves = []
    
    def think(self):
        #Obter um villager randomly
        #Prever se esse villager esta ou nao nos werewolves
        #Se estiver, sabemos que esse e lobisomem e belief nesse passa a 1
        #Caso contrario escolhemos uma estrategia normalmente e aplicamos
        global villager_voting_strategies, all_villagers
        victim = np.random.choice(list(set(all_villagers) -set(self._knownInnocents)))
        if isinstance(victim, Werewolf):
            self._knownWerewolves = self._knownWerewolves + [victim]
            self._belief[victim.getName()][0]=1 #new
        else:
            self._knownInnocents = self._knownInnocents + [victim]
            probabilities = [0.6*self._laziness, 0.8*(100-self._intelligence), 0.8*self._intelligence, 0.8*self._respect, 0.8*self._faith]
            probabilities = [p/sum(probabilities) for p in probabilities] #Normalize
            strategy = np.random.choice(villager_voting_strategies, p=probabilities)
            
            bestKnowStrategy = max(self._Q, key=self._Q.get)
            choices = [strategy, bestKnowStrategy]
            probabilities = [self._stubborness/100, 1-(self._stubborness/100)]
            strategy = np.random.choice(choices, p=probabilities)            
            self._lastStrategy = strategy
            strategy(self)
            self._belief[victim.getName()][0]=0
            normalize_belief(self, 0)
        
    def vote(self):
        global all_villagers, current_voting, total_voting
        for w in self._knownWerewolves:
            if w in all_villagers:
                current_voting[self] = w
                total_voting[self] = total_voting[self] + [w]
                print(self._name + " voted for " + w.getName())
                return
        normalize_belief(self, 0)
        list_to_choose = list(set(all_villagers)-set(self._knownInnocents))
        probabilities = []
        for villager in list_to_choose:
            probabilities = probabilities + [self._belief[villager.getName()][0]]
        probabilities = [i/sum(probabilities) for i in probabilities]
        chosenVillager = np.random.choice(list_to_choose, p=probabilities)
        current_voting[self] = chosenVillager
        total_voting[self] = total_voting[self] + [chosenVillager]
        print(self._name + " voted for " + chosenVillager.getName())

class Doctor(Villager):
    def __init__(self, name):
            super().__init__(name)
            self._medical_skill = random.randint(1,100)
            
    def heal(self):
        global all_villagers, villagers_healed_by_the_doctor
        villager = np.random.choice(all_villagers)
        skill = self._medical_skill*0.01
        probabilities = [skill, 1-skill]
        heal_action=[True, False]
        healing_factor = np.random.choice(heal_action, p=probabilities)
        if(healing_factor):
            villagers_healed_by_the_doctor.append(villager)
        
# ------------------ Helper functions -------------------- #

def setPastQ():
    global all_villagers, werewolves, surviving_villagers, surviving_werewolves, villager_voting_strategies, werewolf_killing_strategies
    Q_vote_villagers = {strategy:0 for strategy in villager_voting_strategies}
    #Average of past villager Q
    for vil in list(set(surviving_villagers)-set(surviving_werewolves)):
        for strategy in villager_voting_strategies:
            Q_vote_villagers[strategy] = Q_vote_villagers[strategy] + vil.getQ()[strategy]
    for strategy in villager_voting_strategies:
        try:
            Q_vote_villagers[strategy] = Q_vote_villagers[strategy] / len(list(set(all_villagers)-set(werewolves)))
        except: pass
    
    Q_vote_werewolves = {strategy:0 for strategy in villager_voting_strategies}
    for vil in surviving_werewolves:
        for strategy in villager_voting_strategies:
            Q_vote_werewolves[strategy] = Q_vote_werewolves[strategy] + vil.getQ()[strategy]
    for strategy in villager_voting_strategies:
        try:
            Q_vote_werewolves[strategy] = Q_vote_werewolves[strategy] / len(surviving_werewolves)
        except: pass
    
    Q_kill_werewolves = {strategy:0 for strategy in werewolf_killing_strategies}
    for vil in surviving_werewolves:
        for strategy in werewolf_killing_strategies:
            Q_kill_werewolves[strategy] = Q_kill_werewolves[strategy] + vil.getQKill()[strategy]
    for strategy in werewolf_killing_strategies:
        try:
            Q_kill_werewolves[strategy] = Q_kill_werewolves[strategy] / len(surviving_werewolves)
        except: pass
        
    for villager in list(set(all_villagers)-set(werewolves)):
        villager.setQ(Q_vote_villagers)
    for werewolf in werewolves:
        werewolf.setQ(Q_vote_werewolves)
        werewolf.setQKill(Q_kill_werewolves)

def getVillager(name):
    for vil in all_villagers:
        if vil.getName() == name:
            return vil

def normalize_belief(villager, index):
    probs = []
    belief = villager.getBelief()
    for tup in belief.values():
        probs = probs + [tup[index]]
    soma = sum(probs)
    for key in belief.keys():
        belief[key][index] = belief[key][index]/soma
    villager.setBelief(belief)

def day():
    global current_voting, all_villagers, werewolves, last_dead_voting, player_name, dead_player
    print("Time to vote\n")
    current_voting = {}
    for villager in all_villagers:
        villager.think() #Belief update
        time.sleep(0.5)
        villager.vote() #Ir ao belief ver as probabilidades de cada um ser o lobo e votar com base nessas probabilidades
    dead_villager = Counter(list(current_voting.values())).most_common(1)[0][0] #Finding the villager who was voted the most
    if dead_villager.getName() == player_name:
        dead_player = True    
    all_villagers.remove(dead_villager)
    del total_voting[dead_villager]
    del current_voting[dead_villager]
    delete_dead_beliefs(dead_villager)
    if isinstance(dead_villager, Werewolf):
        werewolves.remove(dead_villager)
    last_dead_voting = dead_villager
    time.sleep(1)
    print("\n" + dead_villager.getName() + " was the most voted and was killed (he was a " + str(dead_villager.__class__.__name__) + "!)")
    
    for villager in list(set(all_villagers)-set(werewolves)): 
        if isinstance(dead_villager, Werewolf):
            villager.updateQ(dead_villager, 10)
        else:
            villager.updateQ(dead_villager, -10)
    for villager in werewolves:
        if isinstance(dead_villager, Werewolf):
            villager.updateQ(dead_villager, -20)
            villager.updateQKill(dead_villager, -20)
        else:
            villager.updateQ(dead_villager, 10)
            villager.updateQKill(dead_villager, 10)
    villagers_healed_by_the_doctor=[]
    for doctor in doctors:
        doctor.heal()    
    
def night():
    global current_werewolf_voting, all_villagers, werewolves, last_dead_werewolves, dead_player, deadLastVote, deadVoteList
    current_werewolf_voting = []
    for werewolf in werewolves:
        werewolf.voteKill()
    deadVillager = max(set(current_werewolf_voting), key=current_werewolf_voting.count)
    if deadVillager.getName() == player_name:
        dead_player = True
    elif deadVillager in villagers_healed_by_the_doctor:
        print("Doctor saved the victim!")
    else:
        try:
            deadLastVote = current_voting[deadVillager]
            deadVoteList = total_voting[deadVillager]
            del total_voting[deadVillager]
            del current_voting[deadVillager]
        except: pass
        all_villagers.remove(deadVillager)
        delete_dead_beliefs(deadVillager)
        last_dead_werewolves = deadVillager
        time.sleep(0.5)
        print(deadVillager.getName() + " was killed!")

def createPopulation():
    global villagers, werewolves, seers, doctors, all_villagers, total_voting, player_type, player_name
    for i in range(n_villagers - n_seers - n_doctors): #Preencher Villagers normais
        villagers = villagers + [Villager("Villager"+str(i))]
    for j in range(i+1, i+ n_werewolves+1):
        werewolves = werewolves + [Werewolf("Villager" + str(j))]
    for k in range(j+1, j+n_seers+1): #Preencher Seers e Doctors
        seers = seers + [Seer("Villager"+str(k))]
    for d in range(k+1, k+n_doctors+1):
        doctors = doctors + [Doctor("Villager"+str(d))]   
    villagers = villagers + seers + doctors 
    all_villagers = villagers + werewolves
    total_voting = {v:[] for v in all_villagers}
    
    if(player_type == "W"):
        np.random.choice(werewolves).setName(player_name)
    elif(player_type == "V"):
        np.random.choice(list(set(all_villagers)-set(seers)-set(doctors)-set(werewolves))).setName(player_name)
    for villager in all_villagers:
        villager.setBelief(fill_initial_belief(villager))
    

        
# --------------- Strategies for villager voting -------------- #

def ask_someone(villager):
    global all_villagers, werewolves
    belief = villager.getBelief()
    list_to_ask = list(set(all_villagers)-set([villager]))
    if isinstance(villager, Werewolf):
        list_to_ask = list(set(all_villagers)-set(werewolves))
    friend = np.random.choice(list_to_ask)
    suspect = friend.advise(villager)
    if isinstance(villager, Werewolf):
        return suspect
    if suspect == villager:
        return random_strategy(villager)
    belief[suspect.getName()][0] = belief[suspect.getName()][0] * 3
    villager.setBelief(belief)
    normalize_belief(villager, 0)
    

def random_strategy(villager):
    global all_villagers, werewolves
    if isinstance(villager, Werewolf):
        return np.random.choice(list(set(all_villagers)-set(werewolves)))
    belief = villager.getBelief()
    for key in belief.keys():
        belief[key][0] = 1
    villager.setBelief(belief)
    normalize_belief(villager, 0)
    
def dead_last_vote(villager):
    global last_dead_werewolves, deadLastVote
    if isinstance(villager, Werewolf):
        try:
            suspect = deadLastVote
            if suspect not in all_villagers:
                suspect = random_strategy(villager)
        except:
            return random_strategy(villager)
        if not isinstance(suspect, Werewolf):
            return suspect
        else:
            return random_strategy(villager)
    belief = villager.getBelief()
    try:
        suspect = deadLastVote
        belief[suspect.getName()][0] = belief[suspect.getName()][0] * 3
    except:
        return random_strategy(villager)
    villager.setBelief(belief)
    normalize_belief(villager, 0)
    
def dead_most_voted(villager):
    global last_dead_werewolves, total_voting, deadVoteList
    if isinstance(villager, Werewolf):
        try:
            suspect = max(set(deadVoteList)-set([villager]), key=deadVoteList.count)
            if suspect not in all_villagers:
                suspect = dead_last_vote(villager)            
        except:
            return dead_last_vote(villager)
        if not isinstance(suspect, Werewolf):
            return suspect
        else:
            return dead_last_vote(villager)
    belief = villager.getBelief()
    try: #Quando o villager mais votado pelo morto tambem ja morreu ou e o proprio, faz-se antes o ultimo voto do morto
        suspect = max(set(deadVoteList)-set(villager), key=deadVoteList.count)
        belief[suspect][0] = belief[suspect][0] * 3
    except:
        return dead_last_vote(villager)
    villager.setBelief(belief)
    normalize_belief(villager, 0)

def less_respected(villager):
    global all_villagers, werewolves
    if isinstance(villager, Werewolf):
        vil = list(set(all_villagers)-set(werewolves))
        suspect = min(vil, key=attrgetter('_respect'))
        if not isinstance(suspect, Werewolf):
            return suspect
        else:
            return random_strategy(villager)
    belief = villager.getBelief()
    vil = list(set(all_villagers)-set([villager])) #Can't vote himself
    suspect = min(vil, key=attrgetter('_respect'))
    try: 
        belief[suspect.getName()][0] = belief[suspect.getName()][0] * 3
    except:
        return dead_most_voted(villager)    
    villager.setBelief(belief)
    normalize_belief(villager, 0)
    
villager_voting_strategies = [random_strategy, dead_last_vote, dead_most_voted, less_respected, ask_someone]

# ------------ Strategies for werewolf kill voting ------------ #

def kill_seer(werewolf):
    global all_villagers, werewolves
    belief = werewolf.getBelief()
    vil = list(set(all_villagers)-set(werewolves)) #Can't vote for other werewolves
    probabilities = []
    for villager in vil:
        probabilities = probabilities + [belief[villager.getName()][1]]
    probabilities = [i/sum(probabilities) for i in probabilities]
    suspect_seer = np.random.choice(vil, p=probabilities)
    return suspect_seer

def kill_doctor(werewolf):
    global all_villagers, werewolves
    belief = werewolf.getBelief()
    vil = list(set(all_villagers)-set(werewolves)) #Can't vote for other werewolves
    probabilities = []
    for villager in vil:
        probabilities = probabilities + [belief[villager.getName()][2]]
    probabilities = [i/sum(probabilities) for i in probabilities]
    suspect_doctor = np.random.choice(vil, p=probabilities)
    return suspect_doctor

def kill_who_voted_me(werewolf):
    global current_voting
    for villager in current_voting.keys():
        if current_voting[villager] == werewolf:
            return villager
    return kill_randomly(werewolf)

def kill_who_not_voted_me(werewolf):
    global current_voting
    for villager in current_voting.keys():
        if current_voting[villager] != werewolf:
            return villager
    return kill_randomly(werewolf)
        
def kill_randomly(werewolf):
    global all_villagers, werewolves
    victim = np.random.choice(list(set(all_villagers) - set(werewolves)))
    return victim

def kill_most_respected(werewolf):
    global all_villagers, werewolves
    vil = list(set(all_villagers)-set(werewolves)) #Can't vote himself
    victim = max(vil, key=attrgetter('_respect'))
    return victim

def kill_who_voted_me_most(werewolf):
    global all_villagers, werewolves, total_voting
    max_times = 0
    victim = kill_who_voted_me(werewolf)
    for villager in total_voting.keys():
        times = total_voting[villager].count(werewolf)
        if times > max_times:
            max_times = times
            victim = villager
    if victim != None:
        return victim
    else:
        return kill_who_voted_me(werewolf)

werewolf_killing_strategies = [kill_seer, kill_doctor, kill_randomly, kill_most_respected, kill_who_not_voted_me, kill_who_voted_me, kill_who_voted_me_most]

# --------------------- Main Loop ----------------------------- #
    
def MainLoop(firstGame):
    global all_villagers, werewolves, game_mode, player_name, player_type, dead_player, n_doctors, n_seers, n_villagers, n_werewolves,\
    seers, doctors, villagers, last_dead_voting, last_dead_werewolves, current_voting, total_voting, current_werewolf_voting, \
    villagers_healed_by_the_doctor, deadLastVote, deadVoteList, surviving_villagers, surviving_werewolves
    game_mode = input("Select H for history mode and P for player mode: ")
    if(game_mode =="H"):
        print("\n<<< History mode selected >>>\n")    
    if(game_mode =="P"):
        print("\n<<< Player mode selected >>>\n") 
        player_name = input("Please insert your name: ")
        player_type = input("Select W to be a werewolf and V to be a villager: ")     
    createPopulation()
    if not firstGame:
        setPastQ()
    while True:
        time.sleep(0.5)
        print("\nThe night comes...")
        night()
        if len(all_villagers) - len(werewolves) == len(werewolves) or dead_player: 
            break        
        time.sleep(3)
        print("\nAnother day begins...")
        day()
        if len(all_villagers) - len(werewolves) == len(werewolves) or len(werewolves) == 0 or dead_player:
            break        
        time.sleep(3)
    if dead_player == True:
        print("You got killed :(")
    elif(len(werewolves) == 0):
        print("\nAll werewolves were killed... Villagers won!")
    else:
        print("\nThere are as many werewolves as villagers... Werewolves won!")
    choice = input("Do you wish to play again? Y or N : ")
    if choice == "Y":        
        n_villagers = eval(input("How many villagers do you want?: "))
        n_werewolves = eval(input("How many werewolves do you want?: "))
        n_seers = math.ceil(0.1 * n_villagers)
        n_doctors = math.ceil(0.1 * n_villagers)
        surviving_villagers = list(set(all_villagers)-set(werewolves)).copy()
        surviving_werewolves = werewolves.copy()
        werewolves = []
        villagers = []
        seers = []
        doctors = []
        all_villagers = []        
        last_dead_voting = None #Last villager who died in the villager voting
        last_dead_werewolves = None #Last villager who died killed by the werewolves
        current_voting = {}
        total_voting = {v:[] for v in all_villagers} # Villager:Villager voted
        current_werewolf_voting = []
        villagers_healed_by_the_doctor = []
        game_mode = None #Game Mode
        player_name = ""
        player_type = ""
        dead_player = False
        deadLastVote = None
        deadVoteList = []        
        MainLoop(False)

if __name__ == "__main__":
    MainLoop(True)