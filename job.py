class dag_task:

    def __init__(self, job, iter_num, task_type):

        self.parent_job = job
        self.iter_num = iter_num
        self.task_type = task_type # forward, backward, comm
        self.model_size = 100

        self.start_time = -1
        self.end_time = 9999999

    def go_iter(self):
        self.iter_num += 1

    def set_time(self, time):
        self.start_time = time
        self.last_change_time = time
        self.transferred_size = 0
        self.speed = 1
        self.end_time = time + self.model_size / self.speed
        #self.end_time = time + 40

    def is_done(self, time):
        return True if time >= self.end_time else False

    def processing(self, time):
        if time >= self.end_time:
            self.parent_job.sync_comm()
            self.go_iter()

    def __str__(self):
        return str([self.iter_num, self.start_time])

    def update_comm_time(self, time, node):
        old_speed = self.speed
        perf_conf = node.net_conf
        self.transferred_size += (time - self.last_change_time) * self.speed
        rest_size = self.model_size - self.transferred_size
        self.speed = 1 / ((perf_conf["num_of_task"]-1)*perf_conf["eta"] + perf_conf["beta"] * perf_conf["num_of_task"])
        self.end_time = time + rest_size / self.speed
        self.last_change_time = time

        if self.speed != old_speed:
            return "job %d on [%s]: speed: %f, transferred_size: %f, start_time: %f, change_time: %f, end_time: %f, \n" % (self.parent_job.job_id, self.parent_job.get_nodes(), self.speed, self.transferred_size, self.start_time, self.last_change_time, self.end_time)
        else:
            return ""

class dag_job:

    def __init__(self, job_json):

        self.job_conf = job_json
        self.job_id = job_json["job_id"]
        self.nworkers = job_json["nworkers"]
        self.dnn = job_json["dnn"]
        self.dataset = job_json["dataset"]
        self.iters = job_json["iters"]
        self.model_size = job_json["model_size"]
        self.fw_time = job_json["fw_time"]
        self.bw_time = job_json["bw_time"]
    
        self.available_tasks = ["" for i in range(self.job_conf["nworkers"])]
        self.finished_tasks = []

        self.is_communicated = []
        self.is_finished = False

        self.nodes = []
        self.gpus = []

        self.comm_task = dag_task(self, 0, "comm")
        self.is_comm_stall = False

    def add_node(self, node):
        self.nodes.append(node)

    def get_nodes(self):
        return [node.node_id for node in self.nodes]

    def get_slowest_node(self):
        return max(self.nodes, key=lambda x:x.net_conf["num_of_task"])

    def add_gpu(self, gpu):
        self.gpus.append(gpu)

    def is_all_nodes_free(self):
        num_comm = 0
        for node in self.nodes:
            num_comm += len(node.comm_task_list)
        return True if num_comm == 0 else False

    def initial_task(self):

        for i in range(self.nworkers):
            self.available_tasks[i] = {"type": "fw", "iter": 1, "wk_id": i}

        self.is_communicated = [-1 for i in range(self.nworkers)] # -1 mean no communication, 1 mean running communication(waiting synchronous), 0 mean finish synchronous

    def lock_comm(self):
        self.is_comm_stall = True

    def ready_for_comm(self):
        if sum(self.is_communicated) == self.nworkers and not self.is_comm_stall:
            return True
        else:
            return False

    def sync_comm(self):
        self.is_communicated = [-1 for i in range(self.nworkers)]
        self.is_comm_stall = False
        if self.available_tasks[0]["iter"] < self.iters:
            for i in range(self.nworkers):
                self.available_tasks[i]["iter"] += 1
                self.available_tasks[i]["type"] = "fw"
            # reset comm status
            #self.is_communicated = [-1 for i in range(self.nworkers)]
        else:
            self.is_finished = True

    def get_task(self, worker_id):
        return self.available_tasks[worker_id]

    def get_comm(self):
        return self.comm_task

    def pop_task(self, worker_id):

        cur_task = str(self.available_tasks[worker_id])
        if self.available_tasks[worker_id]["type"] == "fw":
            self.available_tasks[worker_id]["type"] = "bw"

        elif self.available_tasks[worker_id]["type"] == "bw":
            self.available_tasks[worker_id]["type"] = "comm"
            self.is_communicated[worker_id] = 1

        #elif self.available_tasks[worker_id]["type"] == "comm":
        #    #self.is_communicated[worker_id] = 0

        #    #if sum(self.is_communicated) == 0:
        #    if self.available_tasks[worker_id]["iter"] < self.iters:
        #        for i in range(self.nworkers):
        #            self.available_tasks[i]["iter"] += 1
        #            self.available_tasks[i]["type"] = "fw"
        #        # reset comm status
        #        #self.is_communicated = [-1 for i in range(self.nworkers)]
        #    else:
        #        self.is_finished = True
            
               
        #return "job-%d %s" % (self.job_id, cur_task)
        return self.job_id, cur_task

    #def is_ready(self, worker_id):
    #    if self.available_tasks[worker_id] != "":
    #        return True
    #    else:
    #        return False
        


