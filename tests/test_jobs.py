from forseti import JobBuilder
import forseti.jobs
import forseti.worker
from forseti.worker import AbsJob2


class SimpleTask(forseti.worker.AbsTask):

    def process(self):
        print("processing")


class SimpleJob(AbsJob2):
    pass
    # def process(self, *args, **kwargs):
    #     print("processing")


class SimpleBuilder(forseti.jobs.AbsJobBuilder):

    @property
    def job(self) -> AbsJob2:
        return SimpleJob()


def test_job_builder():
    builder = JobBuilder(SimpleBuilder())
    builder.add_task(task=SimpleTask())
    job = builder.build_job()
    assert isinstance(job, SimpleJob)
    assert len(job.tasks) == 1
    assert isinstance(job.tasks[0], SimpleTask)
    assert job.progress == 0.0
