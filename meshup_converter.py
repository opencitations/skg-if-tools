import re
import requests
from pprint import pprint
import argparse
from json import load, dump
from index_converter import IndexClassConverter
from meta_converter import MetaClassConverter

class IndexMetaMeshup:
    def __init__(self):
        #self.key = {"authorization": "99f2fcaf-2439-4dfb-a017-d0a95ef74208"}
        self.meta_base_url = "https://w3id.org/oc/meta/api/v1"
        self.index_base_url = "https://w3id.org/oc/index/api/v2"
        self.index_class_converter = IndexClassConverter()
        self.meta_class_converter = MetaClassConverter()
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

    # get citations with API
    def get_citations(self, doi): 
        api_url = f"{self.index_base_url}/references/{doi}"
        response = requests.get(api_url , )  
        if response.status_code == 200:
            cited_json = response.json()
            return cited_json
        else:
            print(f"Error {response.status_code}: {response.text}")
            return None
    
    # get metadata with API
    def get_metadata(self, doi):

        # single DOI
        if isinstance(doi, str):
            doi_encoded = requests.utils.quote(doi) 
            api_url = f"{self.meta_base_url}/metadata/{doi_encoded}"
            response = requests.get(api_url)  

            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error {response.status_code} at URL: {api_url}")
                print(f"Response: {response.text}")
                return None

        # multiple DOIs    
        elif isinstance(doi, list):
            results = []
            for single_doi in doi:
                doi_encoded = requests.utils.quote(single_doi)
                api_url = f"{self.meta_base_url}/metadata/{doi_encoded}"
                response = requests.get(api_url)

                if response.status_code == 200:
                    results.append(response.json())
                else:
                    print(f"Error {response.status_code} at URL: {api_url}")
                    print(f"Response: {response.text}")
                    results.append(None)  

            return results

    def convert (self, doi):
        citations = self.get_citations(doi)  # getting citations with API
        converted_cited = self.index_class_converter.convert(citations)  # converting citations in JSON-LD
        
        self.context["@graph"] = []

        # extracting DOIs of cited products
        for entity in converted_cited["@graph"]:
            if "related_products" in entity and "cites" in entity["related_products"]:
                cites_list = entity["related_products"]["cites"]
                break
        
        # getting metadata for the citing product  
        meta_citing = self.get_metadata(doi)
        converted_meta_citing = self.meta_class_converter.convert(meta_citing) # converting metadata in JSON-LD
        converted_meta_citing[0]["related_products"] = {"cites": cites_list}

        self.context["@graph"].extend(converted_meta_citing)

        # getting metadata for the cited products
        cited_dois = []
        for item in citations:
            matches = re.findall(r'doi:([^\s]+)', item.get('cited', ''))
            cited_dois.extend(matches)
        cited_dois = [f"doi:{doi}" for doi in cited_dois] 
        
        meta_cited = self.get_metadata(cited_dois)
        meta_cited = [d for sublist in meta_cited for d in sublist] # flatten list
        converted_meta_cited = self.meta_class_converter.convert(meta_cited) # converting metadata in JSON-LD

        self.context["@graph"].extend(converted_meta_cited) 
        
        return self.context

    # save to outupt file        
    def save(self, output_file):
        with open(output_file, "w", encoding="utf-8") as f:
            dump(self.context, f, ensure_ascii=False, indent=4)


def main():
    parser = argparse.ArgumentParser(description="Merge metadata and citation data into SKG-IF JSON-LD")
    parser.add_argument("doi", help="The DOI of the citing publication")
    parser.add_argument("output_file", help="Path to save the JSON-LD output file")

    args = parser.parse_args()

    meshup = IndexMetaMeshup()
    meshup.convert(args.doi)
    meshup.save(args.output_file)

    print(f"JSON-LD saved to {args.output_file}")


if __name__ == "__main__":
    main()