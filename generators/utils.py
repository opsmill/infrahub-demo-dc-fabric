import logging

from typing import Dict, List, Optional

from infrahub_sdk import InfrahubClient, InfrahubNode, NodeStore
from infrahub_sdk.batch import InfrahubBatch
from infrahub_sdk.exceptions import GraphQLError

async def upsert_object(
        client: InfrahubClient,
        log: logging.Logger,
        branch: str,
        object_name: str,
        kind_name: str,
        data: Dict,
        store: NodeStore,
        batch: Optional[InfrahubBatch] = None,
        allow_upsert: Optional[bool] = True,
        retrieved_on_failure: Optional[bool] = False,
    ) -> InfrahubNode:
    try:
        obj = await client.create(
            branch=branch,
            kind=kind_name,
            data=data,
        )
        if not batch:
            await obj.save(allow_upsert=allow_upsert)
            log.info(f"- Created {obj._schema.kind} - {object_name}")
        else:
            batch.add(task=obj.save, allow_upsert=allow_upsert, node=obj)
        store.set(key=object_name, node=obj)
    except GraphQLError as exc:
        log.debug(f"- Creation failed for {obj._schema.kind} - {object_name} due to {exc}" )
        if retrieved_on_failure:
            obj = await client.get(kind=kind_name, name__value=object_name)
            store.set(key=object_name, node=obj)
            log.debug(f"- Retrieved {obj._schema.kind} - {object_name}")

    return obj

async def group_add_member(client: InfrahubClient, group: InfrahubNode, members: List[InfrahubNode], branch: str):
    members_str = ["{ id: " + f'"{member.id}"' + " }" for member in members]
    query = """
    mutation {
        RelationshipAdd(
            data: {
                id: "%s",
                name: "members",
                nodes: [ %s ]
            }
        ) {
            ok
        }
    }
    """ % (
        group.id,
        ", ".join(members_str),
    )

    await client.execute_graphql(query=query, branch_name=branch)

async def add_relationships(client: InfrahubClient, node_to_update: InfrahubNode, relation_to_update: str, related_nodes: List[InfrahubNode], branch: str):
    related_node_str = ["{ id: " + f'"{related_node.id}"' + " }" for related_node in related_nodes]
    query = """
    mutation {
        RelationshipAdd(
            data: {
                id: "%s",
                name: "%s",
                nodes: [ %s ]
            }
        ) {
            ok
        }
    }
    """ % (
        node_to_update.id,
        relation_to_update,
        ", ".join(related_node_str),
    )

    await client.execute_graphql(query=query, branch_name=branch)

def populate_local_store(objects: List[InfrahubNode], key_type: str, store: NodeStore):

    for obj in objects:
        key = getattr(obj, key_type)
        if key:
            store.set(key=key.value, node=obj)
