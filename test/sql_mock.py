MOCK_JOB_STATUS = {"value": "test"}
MOCK_JOBS_LIST = ["job1", "job2"]


class SQLMock:
    expected_agreement_id = None
    expected_job_id = None
    expected_owner = None
    stopped_jobs = []
    removed_jobs = []

    @staticmethod
    def assert_all_jobs_stopped_and_reset():
        for job in MOCK_JOBS_LIST:
            assert job in SQLMock.stopped_jobs
        SQLMock.stopped_jobs = []

    @staticmethod
    def assert_all_jobs_removed_and_reset():
        for job in MOCK_JOBS_LIST:
            assert job in SQLMock.removed_jobs
        SQLMock.removed_jobs = []

    @staticmethod
    def assert_expected_params(agreement_id, job_id, owner):
        assert agreement_id == SQLMock.expected_agreement_id
        assert job_id == SQLMock.expected_job_id
        assert owner == SQLMock.expected_owner

    @staticmethod
    def mock_create_sql_job(agreement_id, job_id, owner):
        SQLMock.assert_expected_params(agreement_id, job_id, owner)

    @staticmethod
    def mock_get_sql_jobs(agreement_id, job_id, owner):
        SQLMock.assert_expected_params(agreement_id, job_id, owner)
        return MOCK_JOBS_LIST

    @staticmethod
    def mock_stop_sql_job(job):
        SQLMock.stopped_jobs.append(job)

    @staticmethod
    def mock_remove_sql_job(job):
        SQLMock.removed_jobs.append(job)

    @staticmethod
    def mock_get_sql_status(agreement_id, job_id, owner):
        SQLMock.assert_expected_params(agreement_id, job_id, owner)
        return MOCK_JOB_STATUS
