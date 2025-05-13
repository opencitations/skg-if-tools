# OpenCitations JSON to JSON-LD Converters in SKG-IF format

This repository contains a set of Python converters that transform OpenCitations data from JSON to JSON-LD format following the Scholarly Knowledge Graph Interoperability Framework (SKG-IF).

## Overview

The project consists of three main converters:

1. **IndexClassConverter** - Converts citation data from OpenCitations Index
2. **MetaClassConverter** - Converts metadata from OpenCitations Meta
3. **IndexMetaMeshup** - Combines citation data and metadata for both citing and cited products


## Usage

### Index Converter

Converts citation data from OpenCitations Index to JSON-LD format.

```bash
python index_converter.py input_file.json output_file.jsonld
```

### Meta Converter

Converts metadata from OpenCitations Meta to JSON-LD format.

```bash
python meta_converter.py input_file.json output_file.jsonld
```

### Meshup Converter

Fetches and combines both citation data and metadata for a given identifier (the ones supported by the REST API for OpenCitations Meta), including information for all cited publications.

```bash
python meshup_converter.py "doi:10.7717/peerj-cs.421" output_file.jsonld
```


