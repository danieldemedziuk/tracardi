import json
from datetime import datetime, date
from decimal import Decimal
from tracardi.domain.resource import ResourceCredentials
from tracardi.service.storage.driver import storage
from tracardi.service.plugin.domain.register import Plugin, Spec, MetaData, Form, FormGroup, FormField, FormComponent, \
    Documentation, PortDoc
from tracardi.service.plugin.runner import ActionRunner
from tracardi.service.plugin.domain.result import Result

from .model.configuration import Configuration
from .model.postgresql import Connection


def validate(config: dict) -> Configuration:
    return Configuration(**config)


class PostgreSQLConnectorAction(ActionRunner):

    @staticmethod
    async def build(**kwargs) -> 'PostgreSQLConnectorAction':
        config = validate(kwargs)
        resource = await storage.driver.resource.load(config.source.id)
        return PostgreSQLConnectorAction(config, resource.credentials)

    def __init__(self, config: Configuration, credentials: ResourceCredentials):
        self.credentials = credentials
        self.query = config.query
        self.timeout = config.timeout
        self.db = None

    async def run(self, payload):
        try:

            self.db = await self.credentials.get_credentials(self, Connection).connect()
            result = await self.db.fetch(self.query, timeout=self.timeout)
            result = [self.to_dict(record) for record in result]
            return Result(port="result", value={"result": result})

        except Exception as e:
            self.console.error(str(e))
            return Result(port="error", value={"payload": payload, "error": str(e)})

    async def close(self):
        if self.db:
            await self.db.close()

    @staticmethod
    def to_dict(record):

        def json_default(obj):
            """JSON serializer for objects not serializable by default json code"""

            if isinstance(obj, (datetime, date)):
                return obj.isoformat()

            if isinstance(obj, Decimal):
                return float(obj)

            return str(obj)

        return json.loads(json.dumps(dict(record), default=json_default))


def register() -> Plugin:
    return Plugin(
        start=False,
        spec=Spec(
            module=__name__,
            className='PostgreSQLConnectorAction',
            inputs=["payload"],
            outputs=["result", "error"],
            version='0.6.1',
            license="MIT",
            author="Risto Kowaczewski",
            init={
                "source": {
                    "id": None,
                    "name": None
                },
                "query": None,
                "timeout": 20
            },
            form=Form(groups=[
                FormGroup(
                    name="PostgreSQL resource",
                    fields=[
                        FormField(
                            id="source",
                            name="PostgreSQL resource",
                            description="Select PostgreSQL resource. Authentication credentials will be used to "
                                        "connect to PostgreSQL server.",
                            component=FormComponent(
                                type="resource",
                                props={"label": "resource", "tag": "postgresql"})
                        )
                    ]
                ),
                FormGroup(
                    name="Query settings",
                    fields=[
                        FormField(
                            id="query",
                            name="Query",
                            description="Type SQL Query.",
                            component=FormComponent(type="sql", props={
                                "label": "SQL query"
                            })
                        ),
                        FormField(
                            id="timeout",
                            name="Timeout",
                            description="Type query timeout.",
                            component=FormComponent(type="text", props={
                                "label": "Timeout",

                            })
                        )
                    ])
            ]),

        ),
        metadata=MetaData(
            name='PostgreSQL connector',
            desc='Connects to postgreSQL and reads data.',
            icon='postgres',
            group=["Connectors"],
            documentation=Documentation(
                inputs={
                    "payload": PortDoc(desc="This port takes payload object.")
                },
                outputs={
                    "result": PortDoc(desc="This port query result."),
                    "error": PortDoc(desc="This port gets triggered if an error occurs.")
                }
            )
        )
    )
