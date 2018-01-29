import random
import time
import typing

from forseti import worker
# from frames.tool import SelectDirectory, EggsJob
from forseti.tools.abstool import AbsTool

from forseti.worker import ProcessJob
class Eggs(AbsTool):
    name = "Eggs"
    description = "Sed odio sem, vestibulum a lacus sed, posuere porta neque. Ut urna arcu, dignissim a dolor ac, " \
                  "sollicitudin pellentesque mi. Curabitur feugiat interdum mauris nec venenatis. In arcu elit, " \
                  "scelerisque et bibendum id, faucibus id enim. Proin dui mi, imperdiet eget varius ut, faucibus at " \
                  "lectus. Sed accumsan quis turpis id bibendum. Mauris in ligula nec tortor vulputate vulputate. " \
                  "Nullam tincidunt leo nec odio tincidunt malesuada. Integer ut massa dictum, scelerisque turpis " \
                  "eget, auctor nibh. Vestibulum sollicitudin sem eget enim congue tristique. Cras sed purus ac diam " \
                  "pulvinar scelerisque et efficitur justo. Duis eu nunc arcu"

    def __init__(self) -> None:
        super().__init__()


    @staticmethod
    def new_job() -> typing.Type[worker.ProcessJob]:
        return EggsJob

    @staticmethod
    def discover_jobs(*args, **kwargs):
        jobs = []
        for x in range(10):
            jobs.append({"num": x})
        return jobs

class EggsJob(ProcessJob):
    def process(self, num=0, *args):
        self.log("Making {} eggs".format(num))
        time.sleep(.1)

        self.result = "But I wanted {} Eggs".format(random.randint(1, 1000))

    def on_completion(self, *args, **kwargs):
        self.log("Finished making eggs")