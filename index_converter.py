from json import load, dump
import os
import re
import argparse
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta


class IndexClassConverter:
    def __init__(self):
        self.base = "https://w3id.org/oc/index/"

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

    def create_omid_url(self, string):
        return re.sub(r"^.*omid:([^ ]+).*$", self.base + r"\1", string)

    def create_identifiers(self, string):
        identifiers = []
        for item in string.split():
            if ":" in item:
                scheme, value = item.split(":", 1)
            else:
                scheme, value = "doi", item
            identifiers.append({"scheme": scheme, "value": value})
        return identifiers
    
    def parse_date(self, datetime_string):
        for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
            try:
                dt = datetime.strptime(datetime_string, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        return None

    def create_manifestations_citing(self, datetime_string):
        dt = self.parse_date(datetime_string)
        if dt:
            return dt.isoformat()  
        else: 
            return None
        
    def create_manifestations_cited(self, creation_date, timespan):
        dt = self.parse_date(creation_date)
        if not dt:
            return []

        match = re.match(r"P(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)D)?", timespan)
        if not match:
            return []

        years = int(match.group(1) or 0)
        months = int(match.group(2) or 0)
        days = int(match.group(3) or 0)

        publication_date = (dt - relativedelta(years=years, months=months, days=days)).isoformat()
        return [{"dates": {"publication": publication_date}}]

    def create_related_products(self, string):
        for item in string.split():
            if "omid" in item:
                return self.create_omid_url(item)
            else:
                return item
                
    def convert(self, json_data):
        # checking if input is a file path or json 
        if isinstance(json_data, str) and os.path.isfile(json_data):
            with open(json_data, "r", encoding="utf-8") as f:
                oc_json = load(f)
        else:
            oc_json = json_data
        
        self.context["@graph"] = []

        first_product = oc_json[0]

        citing_product = {
            "local_identifier": self.create_omid_url(first_product["citing"].split()[0]),
            "identifiers": self.create_identifiers(first_product["citing"]),
        }
        if "creation" in first_product:  
            citing_product["manifestations"] = [{"dates": {"publication": self.create_manifestations_citing(first_product["creation"])}}]
        citing_product["related_products"] = {"cites": [self.create_related_products(item["cited"]) for item in oc_json]}

        self.context["@graph"].append(citing_product)
        
        for item in oc_json:
            cited_product = {
                "local_identifier": self.create_omid_url(item["cited"].split()[0]),
                "identifiers": self.create_identifiers(item["cited"]),   
            }
            if "timespan" in item and "creation" in item: 
                cited_product["manifestations"] = self.create_manifestations_cited(item["creation"], item["timespan"])

            self.context["@graph"].append(cited_product)
        return self.context

    def save(self, output_file):
        with open(output_file, "w", encoding="utf-8") as f:
            dump(self.context, f, ensure_ascii=False, indent=4)

        
def main():
    parser = argparse.ArgumentParser(description="Convert JSON to JSON-LD format")
    parser.add_argument("input_file", help="Path to the JSON input file")
    parser.add_argument("output_file", help="Path to save the JSON-LD output file")
    args = parser.parse_args()

    converter = IndexClassConverter()
    converter.convert(args.input_file)
    converter.save(args.output_file)

    print(f"JSON-LD saved to {args.output_file}")

if __name__ == "__main__":
    main()
