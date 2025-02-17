from tracardi.service.plugin.domain.register import Plugin, Spec, MetaData, Documentation, PortDoc, Form, FormGroup, \
    FormField, FormComponent
from tracardi.service.plugin.runner import ActionRunner
from .model.config import Config, MixPanelCredentials
from tracardi.service.storage.driver import storage
from tracardi.domain.resource import ResourceCredentials
from tracardi.process_engine.action.v1.connectors.mixpanel.client import MixPanelAPIClient
from tracardi.service.plugin.domain.result import Result
from datetime import datetime
from fastapi import HTTPException


def validate(config: dict) -> Config:
    return Config(**config)


class MixPanelFunnelFetcher(ActionRunner):

    @staticmethod
    async def build(**kwargs) -> 'MixPanelFunnelFetcher':
        config = Config(**kwargs)
        resource = await storage.driver.resource.load(config.source.id)
        return MixPanelFunnelFetcher(config, resource.credentials)

    def __init__(self, config: Config, credentials: ResourceCredentials):
        self.config = config
        self.client = MixPanelAPIClient(
            **credentials.get_credentials(self, MixPanelCredentials).dict()
        )

    async def run(self, payload):
        if self.config.to_date is None:
            self.config.to_date = datetime.utcnow().strftime("%Y-%m-%d")

        dot = self._get_dot_accessor(payload)
        self.config.from_date = datetime.utcfromtimestamp(dot[self.config.from_date]) if \
            isinstance(dot[self.config.from_date], (int, float)) else dot[self.config.from_date].strftime("%Y-%m-%d") if \
            isinstance(dot[self.config.from_date], datetime) else dot[self.config.from_date]

        self.config.to_date = datetime.utcfromtimestamp(dot[self.config.to_date]) if \
            isinstance(dot[self.config.to_date], (int, float)) else dot[self.config.to_date].strftime("%Y-%m-%d") if \
            isinstance(dot[self.config.to_date], datetime) else dot[self.config.to_date]

        try:
            result = await self.client.fetch_funnel(
                project_id=int(self.config.project_id),
                funnel_id=int(self.config.funnel_id),
                from_date=self.config.from_date,
                to_date=self.config.to_date,
                user_id=self.event.profile.id if self.event.profile is not None else ""
            )
            if len(result["meta"]["dates"]) > 31:
                return Result(port="error", value={"error": "Too much data downloaded"})
            return Result(port="success", value=result)

        except HTTPException as e:
            return Result(port="error", value={"error": str(e)})


def register() -> Plugin:
    return Plugin(
        start=False,
        spec=Spec(
            module=__name__,
            className='MixPanelFunnelFetcher',
            inputs=["payload"],
            outputs=["success", "error"],
            version='0.6.1',
            license="MIT",
            author="Dawid Kruk",
            manual="fetch_mixpanel_funnel_action",
            init={
                "source": {
                    "name": None,
                    "id": None
                },
                "project_id": None,
                "funnel_id": None,
                "from_date": None,
                "to_date": None
            },
            form=Form(
                groups=[
                    FormGroup(
                        name="Plugin configuration",
                        fields=[
                            FormField(
                                id="source",
                                name="MixPanel resource",
                                description="Please select your MixPanel resource containing your service account "
                                            "username, password and server prefix.",
                                component=FormComponent(type="resource", props={"label": "Resource", "tag": "mixpanel"})
                            ),
                            FormField(
                                id="project_id",
                                name="Project ID",
                                description="Here paste in your MixPanel project ID.",
                                component=FormComponent(type="text", props={"label": "Project ID"})
                            ),
                            FormField(
                                id="funnel_id",
                                name="Funnel ID",
                                description="Here paste in your MixPanel funnel's ID.",
                                component=FormComponent(type="text", props={"label": "Funnel ID"})
                            ),
                            FormField(
                                id="from_date",
                                name="Lower time bound",
                                description="Here type the path to the lower bound for your report. This path can point"
                                            " to the field containing a timestamp, a datetime object, or YYYY-MM-DD "
                                            "string.",
                                component=FormComponent(type="dotPath", props={"label": "Lower time bound"})
                            ),
                            FormField(
                                id="to_date",
                                name="Upper time bound",
                                description="Here type in the path to the upper bound for your report, according to "
                                            "same rules as above. This field is optional and will default to now when "
                                            "left empty.",
                                component=FormComponent(type="dotPath", props={"label": "Upper time bound"})
                            )
                        ]
                    )
                ]
            )
        ),
        metadata=MetaData(
            name='Fetch funnel from MixPanel',
            desc='Gets funnel given by ID for current profile.',
            icon='bar-chart',
            group=["Stats"],
            documentation=Documentation(
                inputs={
                    "payload": PortDoc(desc="This port takes payload object.")
                },
                outputs={
                    "success": PortDoc(desc="This port returns fetched funnel when the action was successful."),
                    "error": PortDoc(desc="This port gets triggered when an error occurs.")
                }
            )
        )
    )
