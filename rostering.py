from deap import base
from deap import creator
from deap import tools
from deap import algorithms
import pandas as pd
import json
import csv
import random
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

#import json file
with open('./data.json',encoding="utf-8") as f:
    data=json.load(f)

#-------------------------------------------------------------------------------------------------------------------------
"""
Nurse's information
"""
#讀入排班資訊
class NurseSchedulingProblem:
    def __init__(self):
        self.hardConstraintPenalty=data[1]['HARD_CONSTRAINT_PENALTY']
        self.nurses=data[0]["nurses"]
        self.shiftPreference=data[0]["shiftPreference"]
        self.shiftMin=data[0]["shiftMin"]
        self.shiftMax=data[0]["shiftMax"]

        #每位護士一周最多做多少shifts
        self.maxShiftsPerWeek=data[0]["maxShiftsPerWeek"]

        #生成多少周的資料
        self.weeks=data[1]["weeks"]

        self.shiftPerDay = len(self.shiftMin)
        self.shiftsPerWeek = 7 * self.shiftPerDay

    def __len__(self):
        #共有多少任務要安排
        #return len(self.nurses)*self.shiftsPerWeek*self.weeks
        return len(self.nurses)*(self.shiftsPerWeek*self.weeks+self.shiftPerDay*3)

    def getNurseShifts(self,schedule):
        #將護士與工作製作成Dict，Key=nurse, Value=Corresponding Shifts
        shiftsPerNurse = self.__len__() // len(self.nurses)
        nurseShiftsDict={}
        shiftIndex=0
        for nurse in self.nurses:
            nurseShiftsDict[nurse]=schedule[shiftIndex:shiftIndex+shiftsPerNurse]
            shiftIndex+=shiftsPerNurse
        return nurseShiftsDict

    #HC1 計算第一種衝突次數:連續兩班工作
    def countConsecutiveShiftViolations(self,nurseShiftsDict):
        violations=0
        for nurseShifts in nurseShiftsDict.values():
            for shift1,shift2 in zip(nurseShifts,nurseShifts[1:]):
                if shift1==1 and shift2==1:
                    violations+=1
        return violations

    #HC2 計算第二種衝突次數:每周工作天數超過(超過的天數越多，衝突計次越大)
    def countShiftsPerWeekViolations(self,nurseShiftsDict):
        violations=0
        weeklyShiftsList=[]
        for nurseShifts in nurseShiftsDict.values():
            for i in range(0,self.weeks*self.shiftsPerWeek,self.shiftsPerWeek):
                weeklyShifts=sum(nurseShifts[i:i+self.shiftsPerWeek])
                weeklyShiftsList.append(weeklyShifts)
                if weeklyShifts>self.maxShiftsPerWeek:
                    violations+=weeklyShifts-self.maxShiftsPerWeek
        return weeklyShiftsList,violations
    
    #HC3 計算第三種衝突次數:每班的最大最少護士安排數量
    def countNursesPerShiftViolations(self,nurseShiftsDict):
        totalPerShiftList=[sum(shift) for shift in zip(*nurseShiftsDict.values())]
        violations=0
        for shiftIndex,numOfNurses in enumerate(totalPerShiftList):
            dailyShiftIndex=shiftIndex%self.shiftPerDay
            if (numOfNurses > self.shiftMax[dailyShiftIndex]):
                violations += numOfNurses - self.shiftMax[dailyShiftIndex]
            elif (numOfNurses < self.shiftMin[dailyShiftIndex]):
                violations += self.shiftMin[dailyShiftIndex] - numOfNurses
        return totalPerShiftList, violations
    
    #SC1 計算第四種衝突:與護士喜好班型的衝突
    def countShiftPreferenceViolations(self, nurseShiftsDict):
        violations = 0
        for nurseIndex, shiftPreference in enumerate(self.shiftPreference):
            preference = shiftPreference * (self.shiftsPerWeek // self.shiftPerDay)
            shifts = nurseShiftsDict[self.nurses[nurseIndex]]
            for pref, shift in zip(preference, shifts):
                if pref == 0 and shift == 1:
                    violations += 1
        return violations

    #輸出cost
    def getCost(self,schedule):
        nurseShiftsDict=self.getNurseShifts(schedule)
        consecutiveShiftViolations = self.countConsecutiveShiftViolations(nurseShiftsDict)
        shiftsPerWeekViolations = self.countShiftsPerWeekViolations(nurseShiftsDict)[1]
        nursesPerShiftViolations = self.countNursesPerShiftViolations(nurseShiftsDict)[1]
        shiftPreferenceViolations = self.countShiftPreferenceViolations(nurseShiftsDict)
        #計算cost
        hardContstraintViolations = consecutiveShiftViolations + nursesPerShiftViolations + shiftsPerWeekViolations
        softContstraintViolations = shiftPreferenceViolations
        return self.hardConstraintPenalty * hardContstraintViolations + softContstraintViolations
    
    #輸出排班結果
    def printScheduleInfo(self, schedule):
        fieldname=[]
        for i in range(self.weeks*7+3):
            fieldname.append(str(i+1))
        nurseShiftsDict = self.getNurseShifts(schedule)
        print('result: ')
        for nurse in nurseShiftsDict:  # all shifts of a single nurse
            #print(nurse, ":", nurseShiftsDict[nurse])
            test=[nurseShiftsDict[nurse][i:i+3]for i in range(0,(self.weeks*7+3)*3,3)]
            sult=[nurse]
            for i in test:
                if i==[0,0,1]:
                    sult.append('Night')
                elif i==[0,1,0]:
                    sult.append('Afternoon')
                elif i==[0,0,0]:
                    sult.append('Day-off')
                else:
                    sult.append('Early')
            print(sult)
            with open('./solution.csv','a+',newline="")as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(sult)
                

                
#-------------------------------------------------------------------------------------------------------------------------
"""
Algorithm Part
"""
def eaSimpleWithElitism(population, toolbox, cxpb, mutpb, ngen, stats=None,
             halloffame=None, verbose=__debug__):
    logbook = tools.Logbook()
    logbook.header = ['gen', 'nevals'] + (stats.fields if stats else [])
    invalid_ind = [ind for ind in population if not ind.fitness.valid]
    fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
    for ind, fit in zip(invalid_ind, fitnesses):
        ind.fitness.values = fit
    if halloffame is None:
        raise ValueError("halloffame parameter must not be empty!")
    halloffame.update(population)
    hof_size = len(halloffame.items) if halloffame.items else 0
    record = stats.compile(population) if stats else {}
    logbook.record(gen=0, nevals=len(invalid_ind), **record)
    if verbose:
        print(logbook.stream)
    for gen in range(1, ngen + 1):
        offspring = toolbox.select(population, len(population) - hof_size)
        offspring = algorithms.varAnd(offspring, toolbox, cxpb, mutpb)
        invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
        fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
        for ind, fit in zip(invalid_ind, fitnesses):
            ind.fitness.values = fit
        offspring.extend(halloffame.items)
        halloffame.update(offspring)
        population[:] = offspring
        record = stats.compile(population) if stats else {}
        logbook.record(gen=gen, nevals=len(invalid_ind), **record)
        if verbose:
            print(logbook.stream)
    return population, logbook
#-------------------------------------------------------------------------------------------------------------------------

HARD_CONSTRAINT_PENALTY=data[1]['HARD_CONSTRAINT_PENALTY']
POPULATION_SIZE = data[2]['POPULATION_SIZE']
P_CROSSOVER=data[2]['P_CROSSOVER']
P_MUTATION=data[2]['P_MUTATION']
MAX_GENERATIONS=data[2]['MAX_GENERATIONS']
HALL_OF_FAME_SIZE=data[2]['HALL_OF_FAME_SIZE']
random.seed(42)
toolbox=base.Toolbox()

nsp = NurseSchedulingProblem()
creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
creator.create("Individual", list, fitness=creator.FitnessMin)
toolbox.register("zeroOrOne", random.randint, 0, 1)
toolbox.register("individualCreator", tools.initRepeat, creator.Individual, toolbox.zeroOrOne, len(nsp))
toolbox.register("populationCreator", tools.initRepeat, list, toolbox.individualCreator)

def getCost(individual):
    return nsp.getCost(individual),

toolbox.register("evaluate", getCost)

#toolbox.register("select", tools.selTournament, tournsize=2)
#toolbox.register("select", tools.selRandom)
toolbox.register("select", tools.selBest,fit_attr='fitness')
#toolbox.register("select", tools.selWorst,fit_attr='fitness')
#toolbox.register("select", tools.selRoulette)

#toolbox.register("mate", tools.cxPartialyMatched)
#toolbox.register("mate", tools.cxOrdered)
toolbox.register("mate", tools.cxUniform,indpb=0.7)
#toolbox.register("mate", tools.cxTwoPoints)



toolbox.register("mutate", tools.mutFlipBit, indpb=1.0/len(nsp))
#toolbox.register("mutate", tools.mutGaussian, mu=0,sigma=1,indpb=1.0/len(nsp))

def main():
    #initial generation 0
    population=toolbox.populationCreator(n=data[2]["POPULATION_SIZE"])
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("min", np.min)
    stats.register("avg", np.mean)
    hof = tools.HallOfFame(HALL_OF_FAME_SIZE)

    population, logbook = eaSimpleWithElitism(population, toolbox, cxpb=P_CROSSOVER, mutpb=P_MUTATION,
                                              ngen=MAX_GENERATIONS, stats=stats, halloffame=hof, verbose=True)
    best = hof.items[0]
    print("sample: ")
    print(best)
    print("Final Fitness = ", best.fitness.values[0])
    with open('./solution.csv','w',newline="")as f:
        csvfile=csv.writer(f)
        fieldname=['Name']
        for i in range(data[1]['weeks']*7+3):
            fieldname.append(str(i+1))
        csvfile.writerow(fieldname)
    nsp.printScheduleInfo(best)

    minFitnessValues, meanFitnessValues = logbook.select("min", "avg")

    #sns.set_style("whitegrid")
    Fmin, =plt.plot(minFitnessValues, color='blue',label="minFitnessValues")
    Favg, =plt.plot(meanFitnessValues, color='green',label="meanFitnessValues")
    plt.legend(handles = [Fmin, Favg], loc='upper right')
    plt.xlabel('Generation')
    plt.ylabel('Fitness Value')
    plt.title('Fitness over Generation')
    #plt.title('Min and Average fitness over Generations')
    plt.show()

if __name__ == "__main__":
    main()