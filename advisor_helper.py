# advisor_helper.py
from azure.identity import DeviceCodeCredential
from azure.mgmt.advisor import AdvisorManagementClient

def get_advisor_recommendations(subscription_id):
    credential = DeviceCodeCredential()
    advisor_client = AdvisorManagementClient(credential, subscription_id)

    recommendations = []
    for rec in advisor_client.recommendations.list():
        recommendations.append({
            "Category": rec.category,
            "Impact": rec.impact,
            "ShortDescription": rec.short_description.problem,
            "Solution": rec.short_description.solution,
            "ResourceId": rec.resource_metadata.resource_id
        })

    return recommendations
