import argparse
import os
from json import load, dump
import re
from datetime import timezone, datetime

class MetaClassConverter:
    def __init__(self):
        self.base = "https://w3id.org/oc/meta/" 
        self.type_mapping = {
            "journal article": "http://purl.org/spar/fabio/JournalArticle",
            "book chapter": "http://purl.org/spar/fabio/BookChapter"
        }
        self.venue_mapping = {
            "journal article": "journal",
            "book chapter": "book"
        }
        
        self.context = {
            "@context": [
                "https://w3id.org/skg-if/context/skg-if.json",
                {
                    "@base": "https://w3id.org/skg-if/sandbox/oc/",
                    "skg": "https://w3id.org/skg-if/sandbox/oc/"
                }
            ],
            "@graph": []
        }

    def get_datetime(self, datetime_string):
        try:
            dt = datetime.strptime(datetime_string, "%Y-%m-%d")
        except ValueError:
            try:
                dt = datetime.strptime(datetime_string, "%Y-%m")
            except:
                dt = datetime.strptime(datetime_string, "%Y")

        return dt.replace(tzinfo=timezone.utc).isoformat()

    def get_omid_url(self, string):
        return re.sub(r"^.*omid:([^ ]+).*$", self.base + r"\1", string)

    def create_contributors(self, contributor_list, contributor_type):
        contributors, agents = [], []
        contributor_rank = 0
        
        for contributor in contributor_list:
            if contributor:
                contributor_rank += 1
                match = re.findall(r"^(.+) \[(.+)\]$", contributor)
                if match:
                    name, ids = match[0]
                    contributor_omid = self.get_omid_url(ids)

                    contributor_object = {
                        "by": contributor_omid,
                        "role": contributor_type
                    }
                    if contributor_type != "publisher":
                        contributor_object["rank"] = contributor_rank

                    contributors.append(contributor_object)

                    agent_object = {"local_identifier": contributor_omid}
                    self.create_identifiers(ids, agent_object)

                    if ", " in name:
                        agent_object["entity_type"] = "person"
                        fn, gn = name.split(", ")
                        if gn: agent_object["given_name"] = gn
                        if fn: agent_object["family_name"] = fn
                    else:
                        agent_object["entity_type"] = "organisation" if contributor_type == "publisher" else "agent"
                        if name: agent_object["name"] = name

                    agents.append(agent_object)

        return contributors, agents

    def create_identifiers(self, identifiers, entity):
        for identifier in identifiers.split():
            if "identifiers" not in entity:
                entity["identifiers"] = []
            scheme, value = identifier.split(":", 1)
            entity["identifiers"].append({"scheme": scheme, "value": value}) 

    def convert(self, json_data): 
        # checking if input is a file path or a json
        if isinstance(json_data, str) and os.path.isfile(json_data):
            with open(json_data, "r", encoding="utf-8") as f:
                oc_json = load(f)
        else:
            oc_json = json_data

        # normalizing input
        if isinstance(oc_json, dict):
            oc_json = [oc_json]
        elif isinstance(oc_json, list) and len(oc_json) == 1 and isinstance(oc_json[0], list):
            oc_json = oc_json[0]  # unwrap list-of-list

        self.context["@graph"] = []

        for item in oc_json:
            research_product = {"entity_type": "product"}
            self.context["@graph"].append(research_product)
            
            research_product["local_identifier"] = self.get_omid_url(item["id"])
            self.create_identifiers(item["id"], research_product)

            research_product["product_type"] = (
                "research data" if item["type"] in ("data file", "dataset") else
                "research software" if item["type"] == "software" else
                "literature"
            )

            if "title" in item and item["title"]:
                research_product["titles"] = {"none": item["title"]}

            authors, author_agents = self.create_contributors(item["author"].split("; "), "author")
            editors, editor_agents = self.create_contributors(item["editor"].split("; ") if item["editor"] else [], "editor")
            publishers, publisher_agents = self.create_contributors(item["publisher"].split("; ") if item["publisher"] else [], "publisher")

            research_product["contributions"] = authors + editors + publishers
            self.context["@graph"].extend(agent for agent in author_agents + editor_agents + publisher_agents if agent not in self.context["@graph"])

            manifestation = {
                "type": {
                    "class": self.type_mapping.get(item["type"], ""),
                    "labels": {"en": item["type"]},
                    "defined_in": "http://purl.org/spar/fabio"
                }
            }
            self.create_identifiers(item["id"], manifestation)

            if item["pub_date"]:
                manifestation["dates"] = {"publication": self.get_datetime(item["pub_date"])}

            if any(item.get(k) for k in ("volume", "page", "venue", "issue")):
                manifestation["biblio"] = {}
                if item["issue"]: manifestation["biblio"]["issue"] = item["issue"]
                if item["volume"]: manifestation["biblio"]["volume"] = item["volume"]
                if item.get("page"):
                    if "-" in item["page"]:
                        sp, ep = item["page"].split("-")
                        manifestation["biblio"]["pages"] = {"first": sp, "last": ep}
                    else:
                        manifestation["biblio"]["pages"] = {"first": item["page"], "last": item["page"]}

                if item["venue"]:
                    match = re.findall(r"^(.+) \[(.+)\]$", item["venue"])
                    if match:
                        name, ids = match[0]
                        venue_omid = self.get_omid_url(ids)
                        manifestation["biblio"]["in"] = venue_omid

                        venue_object = {
                            "local_identifier": venue_omid,
                            "entity_type": "venue",
                            "title": name,
                            "type": self.venue_mapping.get(item["type"], "")
                        }
                        self.create_identifiers(ids, venue_object)

                        if editors and self.venue_mapping.get(item["type"]) == "book":
                            venue_object.setdefault("contributions", []).extend(editors)
                        if publishers:
                            venue_object.setdefault("contributions", []).extend(publishers)

                        self.context["@graph"].append(venue_object)

            research_product["manifestations"] = [manifestation]
        
        return self.context["@graph"]

    def save(self, output_file):
        with open(output_file, "w", encoding="utf-8") as f:
            dump(self.context, f, ensure_ascii=False, indent=4)
        
        

def main():
    parser = argparse.ArgumentParser(description="Convert JSON OCDM API format to JSON-LD SKG-IF")
    parser.add_argument("input_file", help="Path to the JSON input file")
    parser.add_argument("output_file", help="Path to save the JSON-LD output file")
    args = parser.parse_args()

    converter = MetaClassConverter()
    converter.convert(args.input_file)
    converter.save(args.output_file)

    print(f"JSON-LD saved to {args.output_file}")

if __name__ == "__main__":
    main()
