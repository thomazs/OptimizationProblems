import random

#  random.seed(1242373)

class Job:
    def __init__(self, p):
        self.p = p
        self.resources = []
        self.successors = []
        self._weight = 0

    def add_resource(self, resource):
        self.resources.append(resource)

    def add_successor(self, successor):
        self.successors.append(successor)

    def weight(self):
        if self._weight == 0:
            self._weight = sum([r for r in self.resources])
        return self._weight


class Ant:

    def __init__(self, aco, idx_ant = 1):
        self.aco = aco
        self.path_done = []
        self.path_todo = [0]
        self.current_position = 0
        self.times_idx = []
        self.times = {}
        self.idx_ant = idx_ant
        self.job_pos = []
        self.job_limit = []

    def get_makespan(self):
        return  max(self.times_idx)

    def can_select_job(self, ijob):
        prec = self.aco.precedence[ijob]
        return all([not (self.job_pos[p] is None) for p in prec])

    def _roullete_values(self):            
        total_pheromone = 0
        const_ctr = 1000
        parts = []
        aco = self.aco
        possible_jobs_todo = filter(lambda j:self.can_select_job(j), self.path_todo)
        # possible_jobs_todo = self.path_todo
        for j in possible_jobs_todo:
            plus_pheromone = aco.get_pheromone(self.current_position, j) * const_ctr * aco.get_job_weight(j)
            parts.append([int(round(total_pheromone,0)), int(round(total_pheromone + plus_pheromone,0))])
            total_pheromone += plus_pheromone
        return int(round(total_pheromone, 0)), parts

    def consume_resources(self, time, to, rss_to_cons):
        for r in range(self.aco.get_qtd_resources()):
            self.times[time][0][r] -= rss_to_cons[r]
        self.times[time][1].append(to)
        self.job_pos[to] = int(time)
    
    def release_resources(self, time, rss_to_release):
        k_time = str(time)        
        if not (time in self.times):
            self.times_idx.append(time)
            self.times[k_time] = [[r for r in self.aco.resources], []]
            return 
        for r in range(self.aco.get_qtd_resources()):
            self.times[k_time][0][r] += rss_to_cons[r]
            if self.times[k_time][0][r] > self.aco.resources[r]:
                self.times[k_time][0][r] = self.aco.resources[r]        

    def calc_time(self, to):
        rss_to_cons = self.aco.jobs[to].resources
        idx_to_use = None
        rss_dif = [0 for r in range(self.aco.get_qtd_resources())]
        pos_current = max(self.job_pos[self.current_position], self.job_limit[to])
        times_to_try = filter(lambda x: x >= pos_current, self.times_idx)
        for t in times_to_try:
            rss_disp = self.times[str(t)][0]
            is_ok = 0
            for r in range(self.aco.get_qtd_resources()):
                rss_dif[r] = rss_disp[r] - rss_to_cons[r]
                is_ok += 1 if rss_dif[r] >= 0 else 0
            if is_ok == self.aco.get_qtd_resources():
                idx_to_use = t
                break

        kidx = str(idx_to_use)
        self.consume_resources(kidx, to, rss_to_cons)
        new_idx = idx_to_use + self.aco.jobs[to].p
        self.release_resources(new_idx, rss_to_cons)
        for s in self.aco.jobs[to].successors:
            self.job_limit[s] = max(self.job_limit[s], idx_to_use+1)

    def add_path(self, to):
        self.path_done.append(to)
        if to in self.path_todo:
            self.path_todo.remove(to)
        self.path_todo += self.aco.jobs[to].successors
        self.path_todo = list(set(self.path_todo))
        if 0 in self.path_todo:
            self.path_todo.remove(0)
        id_last = len(self.aco.jobs) - 1
        if id_last in self.path_todo:
            self.path_todo.remove(id_last)
        self.aco.add_path(self.current_position, to)
        self.calc_time(to)
        self.current_position = to

    def select_path(self):
        if len(self.path_todo) == 0 and len(self.path_done) > 0:
            return None
        
        if len(self.path_todo) == 0 and len(self.path_done) == 0:
            self.path_todo += self.aco.jobs[self.current_position].successors
            
        roulette_data = self._roullete_values()
        roulette_point = random.randint(1, roulette_data[0])
        for i, j in enumerate(roulette_data[1]):
            if roulette_point >= j[0] and roulette_point < j[1]:
                return self.path_todo[i]
        return None
    
    def walk(self):
        if self.current_position == 0 :
            self.path_todo = [s for s in self.aco.jobs[0].successors]
            self.times_idx = [1]
            self.times = {'1': [[r for r in self.aco.resources], []]}
            self.job_pos = [1 if i == 0 else None for i in range(len(self.aco.jobs))]
            self.job_limit = [0 for i in range(len(self.aco.jobs))]
            
        to = self.select_path()

        # se não tem pra onde ir, é porque percorreu tudo e finaliza
        if to is None:
            return False

        self.add_path(to)
        return False


class ACO_RCPSP:

    def __init__(self, ant_count = 10, pheromone_increment = 1.0, pheromone_evaporation = 0.0001, iterations = 10, instance = None):
        self.ant_count = ant_count
        self.pheromone_increment = pheromone_increment
        self.pheromone_evaporation = pheromone_evaporation
        self.resources = []
        self.jobs = []
        self.iterations = iterations
        self.instance = instance
        self.clear_instance()
        self.paths = {}
        self.initial_pheromone = 0.01
        self._max_value_rss = 0
        self._qtd_resources = 0
        self._delta = {}
        self.precedence = []

    def get_qtd_resources(self):
        if self._qtd_resources == 0:
            self._qtd_resources = len(self.resources)
        return self._qtd_resources

    def get_job_weight(self, ijob):
        """
        Aqui está sendo usado pois ao aplicar ACO no caixeiro viajante, o peso é 
        dado pela distância no grafo. No problema que atuamos não temos essa distância,
        então foi usado como lógica aplicar um maior peso, quanto menor o consumo de 
        recursos. Como não temos o critério de urgência das tarefas, isso pode ser 
        usado para tentar realizar o máximo de jobs em uma mesma porção de tempo
        """
        _m = self.get_max_rss()
        _w = self.jobs[ijob].weight()
        return _m - _w

    def get_pheromone(self, from_, to):
        key = self.key(from_, to)
        if not (key in self.paths):
            self.paths[key] = self.initial_pheromone
        return self.paths[key]

    def clear_instance(self) :
        self.times = []
        self.accumulated = 0
        self.better = 0
        self.ants = self.create_ants()

    def create_ants(self):
        return [Ant(self, i+1) for i in range(self.ant_count)]

    def set_instance(self, instance):
        self.instance = instance

    def set_resources(self, resources):
        self.resources = resources

    def add_job(self, job):
        self.jobs.append(job)        

    def key(self, from_, to):
        a, b = min(from_, to), max(from_, to)
        return f'{a}-{b}'

    def add_path(self, from_, to):
        key = self.key(from_, to)
        ac = self.get_pheromone(from_, to)
        self._delta.setdefault(key, 0)
        self._delta[key] += self.pheromone_increment
    
    def update_path_pheromone(self):
        for k in self.paths:
            self.paths[k] = self._delta.get(k, 0) - self.pheromone_evaporation
            if self.paths[k] < 0:
                self.paths[k] = self.initial_pheromone
        self._delta = {}

    def set_max_rss(self):
        self._max_value_rss = sum([r + 1 for r in self.resources])

    def get_max_rss(self):
        if (self._max_value_rss == 0):
            self.set_max_rss()
        return self._max_value_rss

    def execute_iteration(self, iteration):
        self.clear_instance()
        for i in range(len(self.jobs)):
            for ant in self.ants:
                ant.walk()
            self.update_path_pheromone()

    def mount_precedence(self):
        self.precedence = [[] for j in self.jobs]
        for i in range(1, len(self.jobs)):
            for s in self.jobs[i].successors:
                self.precedence[s].append(i)

    def execute(self):
        self.set_max_rss()
        self.mount_precedence()
        best = None
        qty = 0
        for i in range(self.iterations):
            self.execute_iteration(i)

            for a in self.ants:
                if best is None or a.get_makespan() < best.get_makespan():
                    qty = 1
                    best = a
                elif a.get_makespan() == best.get_makespan():
                    qty += 1
        return best, qty
                    
        

    @classmethod
    def read_file_instance(cls, filename, ant_count = 10, pheromone_increment = 1.0, pheromone_evaporation = 0.0001, iterations = 10):
        aco = ACO_RCPSP(ant_count, pheromone_increment, pheromone_evaporation, iterations)

        rvalue = lambda row, position : int(row[position:position+8].strip())
        lines = open(filename).readlines()
        
        instance = filename[3:].split('.')[0].replace('_', '.')
        aco.set_instance(instance)

        qtd_jobs = rvalue(lines[0], 0)
        qtd_rss = rvalue(lines[0], 8)

        pos = 0
        cap_rss = []
        for i in range(qtd_rss):
            cap_rss.append(rvalue(lines[1], pos))
            pos += 8
        aco.set_resources(cap_rss)
        
        for i in range(2, 2 + qtd_jobs):
            if len(lines[i].strip()) < 10:
                    continue
            job = Job(rvalue(lines[i], 0))
            qty_successors = rvalue(lines[i], 40)

            pos = 8
            for j in range(qtd_rss):
                job.add_resource(rvalue(lines[i], pos))
                pos += 8
                
            pos = 48
            for j in range(qty_successors):
                job.add_successor(rvalue(lines[i], pos)-1)
                pos += 8

            aco.add_job(job)            

        return aco


def executa_teste():
    aco = ACO_RCPSP.read_file_instance('X1_1.RCP', ant_count=10, iterations=5)
    best_ant, repetitions = aco.execute()
    print('Makespan: ', best_ant.get_makespan(), '  - Found in',  repetitions,' ant(s)')
    return aco, best_ant

def see_solution(ant):
    for k in ant.times:
            print('%.2d'%int(k), ' => ', list(map(lambda i: i + 1, ant.times[k][1])))

aco, ba = executa_teste()
see_solution(ba)
