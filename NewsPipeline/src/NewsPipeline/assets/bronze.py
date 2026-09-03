"""
NewsPipeline/assets/bronze.py — Bronze Asset: Collect raw article links from RSS feeds partitioned by day.
"""

from typing import Any

from dagster import Output, asset

from NewsPipeline.partitions import daily_partitions, url_to_article_id
from NewsPipeline.resources.rss_resource import RSSResource


@asset(
    group_name="bronze",
    partitions_def=daily_partitions,
    io_manager_key="mongo_io_manager",
    description="Scan RSS feeds and collect candidate article links for the given daily partition.",
)
def bronze_links(context, rss_resource: RSSResource) -> Output[list[dict[str, Any]]]:
    """
    Partitioned per day (partition_key = 'YYYY-MM-DD').
    Fetches RSS entries matching the partition date, assigns deterministic article_id,
    and returns document list to be persisted into MongoDB collection 'bronze_links'.
    """
    target_date = context.partition_key
    links = rss_resource.fetch_links(target_date=target_date)

    # Attach IDs and partition metadata
    for item in links:
        item["article_id"] = url_to_article_id(item["url"])
        item["partition_date"] = target_date

    context.log.info(f"Bronze: Collected {len(links)} links for date {target_date}.")

    return Output(
        value=links,
        metadata={
            "links_collected": len(links),
            "partition_date": target_date,
        },
    )
