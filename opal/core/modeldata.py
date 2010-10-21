import os
import string
import types
import time
import shutil
import log
import copy

from opal import config
from opal.core.measure import MeasureValueTable
from opal.core.testproblem import TestProblem

class TestResult:


    def __init__(self,
                 testIsFailed=None,
                 testNumber=None,
                 problems=None,
                 parameters=None,
                 measureValueTable=None,
                 **kwargs):
        self.test_is_failed = testIsFailed
        self.test_number = testNumber
        self.problems = problems
        self.parameters = parameters
        self.measure_value_table = measureValueTable
        pass
    


# =============================
class ModelData:
    """ 
    This class represents a data generator for a parameter optimization
    problem. The data is the values of the elementary measures that are needed
    to formulate the problem. To specify a data generator, we need provide:

    1. The algorithm 
    2. the set of elementary measures concerned 
    3. the set of parameters to control
    4. the test problems set.
    """

    def __init__(self, algorithm, problems, activeParameters,
                platform=config.platform, logging=log.TestLogging(), **kwargs):
        # The core variables
        self.algorithm = algorithm
        if (problems is None) or (len(problems) == 0):
            self.problems = [TestProblem(name='TESTPROB')]
        else:
            self.problems = problems
        
        self.parameters = activeParameters

        # active_parameters_names are the name of parameters that are
        # variables in the parameter optimization problem.
        # The other parameters remain fixed.
        self.active_parameter_names = [par.name for par in activeParameters]
        for param in self.parameters:
            if param.name not in self.active_parameter_names:
                param.set_as_const()
        
        #self.parameters = copy.deepcopy(algorithm.parameters)
        self.measures = copy.deepcopy(algorithm.measures)
        
        # TODO
        # This is unrelated to the model data. It should be moved elsewhere.
        self.platformName = ''
        self.platform = platform

        self.logging = logging

        # The monitor variables
        self.test_number = 0
        self.run_id = None

        # The output
        self.test_is_failed = False
        pNames = [prob.name for prob in self.problems]
        mNames = [measure.name for measure in self.measures]
        self.measure_value_table = MeasureValueTable(problem_names=pNames,
                                                     measure_names=mNames)
        # Set options
        self.set_options(**kwargs)
        pass


    def set_options(self,**kwargs):
        # set the log file
        if 'logFile' in kwargs.keys():
            self.logFileName  = os.path.join(os.getcwd(), logFile)
        else:
            self.logFileName  = os.path.join(os.getcwd(), 'test-bed.log')
        return


    def get_active_parameters(self):
        return [param for param in self.parameters if not param.is_const()]


    def fill_parameter_value(self,values):
        j = 0
        for i in range(len(self.parameters)):
            if not self.parameters[i].is_const():
                self.parameters[i].set_value(values[j])
                j = j + 1
        return


    def run(self,parameter_values):
        self.fill_parameter_value(parameter_values)
        #print '[modeldata.py]',[param.value for param in self.parameters]
        self.test_number += 1
        self.test_is_failed = False
        if not self.algorithm.are_parameters_valid(self.parameters):
            #print '[modeldata.py]','Parameter values are invalid, test fails'
            self.test_is_failed = True
            return
        #print '[modeldata.py]','Parameter values are valid'
        
        ltime = time.localtime()
        self.run_id = str(ltime.tm_year) +  str(ltime.tm_mon) + str(ltime.tm_mday) + \
                 str(ltime.tm_hour) + str(ltime.tm_min) + str(ltime.tm_sec)
        # Launches the algorithm routines
        
        self.algorithm.set_parameter(self.parameters)
        
        for prob in self.problems:
            #print '[modeldata.py]:Executing ' + prob
            #if self.algorithm.get_output() is None:
                # The algorithm out the measues to standard output
                # We will redirect the output to the corresponding measure file
                # Otherwise, the output of runing is outed to the /dev/null
            #    output_file_name = algorithm.get_measure_file(prob)
            #else:
            #    output_file_name = '/dev/null'
            #output_file_name = self.algorithm.name + '-' + prob.name + '.out'
            self.platform.execute(self.algorithm.get_full_executable_command(self.parameters, prob),
                                  commandId=self.run_id + '-' + prob.name)
        return 

    def get_test_result(self):
        self.measure_value_table.clear()
        if self.test_is_failed is True:
            return TestResult(testIsFailed=True)
        resultIsReady = "ended(" + self.run_id + "*-LSF)"
        self.platform.waitForCondition(resultIsReady)

        for prob in self.problems:
            measure_values = self.algorithm.get_measure(prob,self.measures)
            #print measure_values
            if len(measure_values) != 0:
                self.measure_value_table.add_problem_measures(prob.name,measure_values)
        #print "ho ho test.py ",self.problems
        return TestResult(testIsFailed=False,
                          testNumber=self.test_number,
                          problems=self.problems,
                          parameters=self.parameters,
                          measureValueTable=self.measure_value_table)

    def synchronize_measures(self):
        for i in range(len(self.measures)):
            tmp = self.measures[i]
            self.measures[i] = self.measures[i].get_global_object()
            del tmp
        # Resolve the link betwwen the measure functions and the value table
        return

    def log(self,fileName):
        self.logging.write(self,fileName)
    
    def reduce_problem_set(self):
        newProblemSet = []
        i = 1
        for prob in self.problems:
            if i % 2 == 0:
                newProblemSet.append(prob)
            i = i + 1
        activeParameters = self.get_active_parameters()
        reducedData = ModelData(algorithm=self.algorithm,
                                problems=newProblemSet,
                                activeParameters=activeParameters,
                                platform=self.platform)
        return reducedData

        
        
