from cloudify_rest_client.responses import ListResponse


class ExecutionSchedule(dict):
    """
    Cloudify execution schedule.
    """

    def __init__(self, execution_schedule):
        super(ExecutionSchedule, self).__init__()
        self.update(execution_schedule)

    @property
    def id(self):
        """
        :return: The name of the execution schedule.
        """
        return self.get('id')

    @property
    def deployment_id(self):
        """
        :return: The deployment's id which the scheduled execution is
        related to.
        """
        return self.get('deployment_id')

    @property
    def workflow_id(self):
        """
        :return: The id of the workflow which the scheduled execution runs.
        """
        return self.get('workflow_id')

    @property
    def parameters(self):
        """
        :return: The scheduled execution's parameters
        """
        return self.get('parameters') or {}

    @property
    def created_at(self):
        """
        :return: Timestamp of the execution schedule creation.
        """
        return self.get('created_at')

    @property
    def next_occurrence(self):
        """
        :return: The calculated next date and time in which the scheduled
        workflow should be executed at.
        """
        return self.get('next_occurrence')

    @property
    def since(self):
        """
        :return: The earliest date and time the scheduled workflow should be
        executed at.
        """
        return self.get('since')

    @property
    def until(self):
        """
        :return: The latest date and time the scheduled workflow may be
        executed at (if any).
        """
        return self.get('until')

    @property
    def stop_on_fail(self):
        """
        :return: Whether the scheduler should stop attempting to run the
        execution once it failed.
        """
        return self.get('stop_on_fail')


class ExecutionSchedulesClient(object):

    def __init__(self, api):
        self.api = api
        self._uri_prefix = 'execution-schedules'

    def create(self, schedule_id, deployment_id, workflow_id,
               execution_arguments=None, parameters=None,
               since=None, until=None, frequency=None, count=None,
               weekdays=None, rrule=None, slip=0, stop_on_fail=False):
        """Schedules a deployment's workflow execution whose id is provided.

        :param schedule_id: Name for the schedule task. Used for listing,
            updating or deleting it later.
        :param deployment_id: The deployment's id to execute a workflow for.
        :param workflow_id: The workflow to be executed id.
        :param execution_arguments: A dict of arguments passed directly to the
            workflow execution. May contain the following keys:
            - allow_custom_parameters: bool
            - force: bool
            - dry run: bool
            - queue: bool
            - wait after fail: integer
            See Executions for more details on these.
        :param parameters: Parameters for the workflow execution.
        :param since: A string representing the earliest date and time this
            workflow should be executed at. Must be provided if no `rrule` is
            given.
        :param until: A string representing the latest date and time this
            workflow may be executed at. May be empty.
        :param frequency: A string representing the frequency with which to
            run the execution, e.g. '2 weeks'. Must be provided if no `rrule`
            is given and `count` is other than 1.
        :param count: Maximum number of times to run the execution.
            If left empty, there's no limit on repetition.
        :param weekdays: A string representing the weekdays on which to run
            the execution, e.g. 'su,mo,tu'. If left empty, the execution will
            run on any weekday.
        :param rrule: A string representing a scheduling rule in the
            iCalendar format, e.g. 'RRULE:FREQ=DAILY;INTERVAL=3', which means
            "run every 3 days". Overrides `frequency`, `count` and `weekdays`.
        :param slip: Maximum time window after the target time has passed,
            in which the scheduled execution can run (in minutes).
        :param stop_on_fail: If set to true, once the execution has failed,
            the scheduler won't make further attempts to run it.
        :return: The created execution schedule.
        """
        assert schedule_id
        assert deployment_id
        assert workflow_id
        assert since
        data = {
            'deployment_id': deployment_id,
            'workflow_id': workflow_id,
            'execution_arguments': execution_arguments,
            'parameters': parameters,
            'since': since.isoformat(),
            'until': until.isoformat() if until else None,
            'frequency': frequency,
            'count': count,
            'weekdays': weekdays.split(',') if weekdays else None,
            'rrule': rrule,
            'slip': slip,
            'stop_on_fail': str(stop_on_fail).lower()
        }
        uri = '/{self._uri_prefix}/{id}'.format(self=self, id=schedule_id)
        response = self.api.put(uri,
                                data=data,
                                expected_status_code=201)
        return ExecutionSchedule(response)

    def update(self, schedule_id, since=None, until=None, frequency=None,
               count=None, weekdays=None, rrule=None, slip=None,
               stop_on_fail=None):
        """Updates scheduling parameters of an existing execution schedule
        whose id is provided.

        :param schedule_id: Name for the schedule task. Used for listing,
            updating or deleting it later.
        :param since: A string representing the earliest date and time this
            workflow should be executed at. Must be provided if no `rrule` is
            given.
        :param until: A string representing the latest date and time this
            workflow may be executed at. May be empty.
        :param frequency: A string representing the frequency with which to
            run the execution, e.g. '2 weeks'. Must be provided if no `rrule`
            is given and `count` is other than 1.
        :param count: Maximum number of times to run the execution.
            If left empty, there's no limit on repetition.
        :param weekdays: A string representing the weekdays on which to run
            the execution, e.g. 'su,mo,tu'. If left empty, the execution will
            run on any weekday.
        :param rrule: A string representing a scheduling rule in the
            iCalendar format, e.g. 'RRULE:FREQ=DAILY;INTERVAL=3', which means
            "run every 3 days". Overrides `frequency`, `count` and `weekdays`.
        :param slip: Maximum time window after the target time has passed,
            in which the scheduled execution can run (in minutes).
        :param stop_on_fail: If set to true, once the execution has failed,
            the scheduler won't make further attempts to run it.

        :return: The updated execution schedule.
        """
        assert schedule_id
        data = {
            'since': since.isoformat() if since else None,
            'until': until.isoformat() if until else None,
            'frequency': frequency,
            'count': count,
            'weekdays': weekdays.split(',') if weekdays else None,
            'rrule': rrule,
            'slip': slip,
            'stop_on_fail': str(stop_on_fail).lower() if stop_on_fail else None
        }
        uri = '/{self._uri_prefix}/{id}'.format(self=self, id=schedule_id)
        response = self.api.patch(uri,
                                  data=data,
                                  expected_status_code=201)
        return ExecutionSchedule(response)

    def delete(self, schedule_id):
        """
        Deletes the execution schedule whose id matches the provided id.

        :param schedule_id: The id of the schedule to be deleted.
        """
        assert schedule_id
        self.api.delete('/{self._uri_prefix}/{id}'.format(self=self,
                                                          id=schedule_id),
                        expected_status_code=204)

    def list(self, _include=None, sort=None, is_descending=False, **kwargs):
        """
        Returns a list of currently existing execution schedules.

        :param _include: List of fields to include in response.
        :param sort: Key for sorting the list.
        :param is_descending: True for descending order, False for ascending.
        :param kwargs: Optional filter fields. For a list of available fields
               see the REST service's models.Execution.fields
        :return: Schedules list.
        """
        params = kwargs
        if sort:
            params['_sort'] = '-' + sort if is_descending else sort

        response = self.api.get('/{self._uri_prefix}'.format(self=self),
                                params=params, _include=_include)
        return ListResponse([ExecutionSchedule(item)
                             for item in response['items']],
                            response['metadata'])

    def get(self, schedule_id, _include=None):
        """Get an execution schedule by its id.

        :param schedule_id: Id of the execution schedule to get.
        :param _include: List of fields to include in response.
        :return: Execution.
        """
        assert schedule_id
        uri = '/{self._uri_prefix}/{id}'.format(self=self, id=schedule_id)
        response = self.api.get(uri, _include=_include)
        return ExecutionSchedule(response)