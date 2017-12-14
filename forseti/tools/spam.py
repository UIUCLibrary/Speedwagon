import random
import time
import typing

from forseti.worker import ProcessJob
from forseti import worker
# from frames.tool import SelectDirectory, DummyJob
from forseti.tools.abstool import AbsTool


class Spam(AbsTool):
    name = "Spam"
    description = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Proin ac diam id purus pretium " \
                  "venenatis. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia " \
                  "Curae; Fusce laoreet fermentum lorem et pretium. Duis iaculis venenatis sagittis. Nulla tristique " \
                  "tellus at dolor laoreet maximus. Aenean ac posuere augue, quis volutpat felis. Phasellus egestas " \
                  "orci id erat fringilla, in euismod purus luctus. Proin faucibus condimentum imperdiet. Lorem " \
                  "ipsum dolor sit amet, consectetur adipiscing elit. Pellentesque porttitor eu erat at congue. " \
                  "Quisque feugiat pulvinar eleifend. Nulla tincidunt nibh velit, non fermentum lorem pharetra at. " \
                  "Sed eleifend sapien ut faucibus convallis. Orci varius natoque penatibus et magnis dis parturient " \
                  "montes, nascetur ridiculus mus. Nullam lacinia sed augue quis iaculis. Aliquam commodo dictum mi, " \
                  "non semper quam varius ut."

    def __init__(self) -> None:
        super().__init__()

        # input_data = SelectDirectory()
        # input_data.label = "Input"
        # self.options.append(input_data)
        #
        # output_data = SelectDirectory()
        # output_data.label = "Output"
        # self.options.append(output_data)

    def new_job(self) -> typing.Type[worker.ProcessJob]:
        return DummyJob
        # return DummyJob()

    @staticmethod
    def discover_jobs(*args, **kwargs):
        for x in range(100):
            yield {"num": x}

class DummyJob(ProcessJob):
    def process(self, num=0, *args):
        self.log("{} ---STarting something".format(num))
        time.sleep(.1)

        self.result = "My result {}".format(random.randint(1, 1000))
        # return

    def on_completion(self):
        self.log("---ending something")
