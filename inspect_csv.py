import csv
import json

def inspect_csv(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        sample_row = next(reader)
        
        print("Fields:")
        for field in fields:
            print(f"- {field}")
            
        print("\nSample Row:")
        print(json.dumps(sample_row, indent=2))

if __name__ == '__main__':
    inspect_csv('f:/CUBE-Returns-Manager/data/returns_sample.csv')
