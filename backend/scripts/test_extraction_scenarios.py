"""
Automated test scenarios for Valido extraction and validation
Tests various field extraction patterns, validations, and edge cases
"""
import requests
import json
import time
from pathlib import Path
import os

BASE_URL = "http://127.0.0.1:8000"

# Try to find PDF in multiple locations
POSSIBLE_PATHS = [
    r"D:\Valido\PSTI_Letter of Intent - Abhishek Rai(verified) (1).pdf",
    r"D:\Valido\test_docs\PSTI_Letter of Intent - Abhishek Rai(verified) (1).pdf",
    str(Path(__file__).parent.parent.parent / "PSTI_Letter of Intent - Abhishek Rai(verified) (1).pdf"),
]

PDF_PATH = POSSIBLE_PATHS[0]  # Default to first path
for path in POSSIBLE_PATHS:
    if Path(path).exists():
        PDF_PATH = str(path)
        print(f"✓ Found PDF at: {PDF_PATH}")
        break
else:
    print("⚠️ WARNING: PDF not found in any of these locations:")
    for path in POSSIBLE_PATHS:
        print(f"  - {path}")
    print(f"   Using default path: {PDF_PATH}")

# Test scenarios based on the actual PDF content
TEST_SCENARIOS = [
    {
        "name": "Basic Salary Extraction",
        "description": "Extract monthly salary from compensation table",
        "rules": {
            "fields": [
                {
                    "name": "Monthly Salary",
                    "lookFor": "Monthly Pay before Income Tax",
                    "type": "number",
                    "strategy": "first",
                    "validations": []
                }
            ],
            "validations": {"signed": True}
        },
        "expected": {
            "Monthly Salary": "₹ 1,66,979"
        }
    },
    
    {
        "name": "Annual CTC Extraction",
        "description": "Extract annual CTC from offer details",
        "rules": {
            "fields": [
                {
                    "name": "Annual CTC",
                    "lookFor": "INR.",
                    "type": "text",
                    "strategy": "first",
                    "validations": []
                }
            ],
            "validations": {}
        },
        "expected": {
            "Annual CTC": "21,06,228/-"  # Looking for "INR." (with period) to get the number
        }
    },
    
    {
        "name": "Date Extraction",
        "description": "Extract offer letter date",
        "rules": {
            "fields": [
                {
                    "name": "Letter Date",
                    "lookFor": "Date:",
                    "type": "date",
                    "strategy": "first",
                    "validations": []
                }
            ],
            "validations": {}
        },
        "expected": {
            "Letter Date": "21st August 2024"
        }
    },
    
    {
        "name": "Multiple Fields Extraction",
        "description": "Extract salary, PF, and professional tax",
        "rules": {
            "fields": [
                {
                    "name": "Gross Salary Monthly",
                    "lookFor": "Gross Salary",
                    "type": "number",
                    "strategy": "first",
                    "validations": []
                },
                {
                    "name": "PF Employee",
                    "lookFor": "PF Employee",
                    "type": "number",
                    "strategy": "first",
                    "validations": []
                },
                {
                    "name": "Professional Tax",
                    "lookFor": "Professional Tax",
                    "type": "number",
                    "strategy": "first",
                    "validations": []
                }
            ],
            "validations": {}
        },
        "expected": {
            "Gross Salary Monthly": "₹ 1,68,979",
            "PF Employee": "₹ 1,800",
            "Professional Tax": "₹ 200"
        }
    },
    
    {
        "name": "Text Validation - Min Length",
        "description": "Extract candidate name with minimum length validation",
        "rules": {
            "fields": [
                {
                    "name": "Candidate Name",
                    "lookFor": "Mr.",
                    "type": "text",
                    "strategy": "first",
                    "validations": [
                        {"type": "minLength", "value": 5}
                    ]
                }
            ],
            "validations": {}
        },
        "expected": {
            "Candidate Name": "Abhishek Rai,"
        }
    },
    
    {
        "name": "Email Extraction with Pattern Validation",
        "description": "Extract email and validate pattern",
        "rules": {
            "fields": [
                {
                    "name": "Email",
                    "lookFor": "Email ID:",
                    "type": "text",
                    "strategy": "first",
                    "validations": [
                        {"type": "pattern", "value": r".*@.*\.com"}
                    ]
                }
            ],
            "validations": {}
        },
        "expected": {
            "Email": "abhishek.rai8992@gmail.com"
        }
    },
    
    {
        "name": "Phone Number Extraction",
        "description": "Extract contact number",
        "rules": {
            "fields": [
                {
                    "name": "Contact Number",
                    "lookFor": "Contact No",
                    "type": "text",
                    "strategy": "first",
                    "validations": []
                }
            ],
            "validations": {}
        },
        "expected": {
            "Contact Number": "+91-9818084139"
        }
    },
    
    {
        "name": "Position/Role Extraction",
        "description": "Extract job position",
        "rules": {
            "fields": [
                {
                    "name": "Position",
                    "lookFor": "in the capacity of",
                    "type": "text",
                    "strategy": "first",
                    "validations": []
                }
            ],
            "validations": {}
        },
        "expected": {
            "Position": "Senior Developer –Google Cloud Plaƞorm"
        }
    },
    
    {
        "name": "Document Contains Text",
        "description": "Verify document contains specific company name",
        "rules": {
            "fields": [],
            "validations": {
                "signed": True,
                "must_contain": {
                    "text": "Pi Square Technologies",
                    "case_sensitive": False
                }
            }
        },
        "expected": {}
    },
    
    {
        "name": "Probation Period Extraction",
        "description": "Extract probation period duration",
        "rules": {
            "fields": [
                {
                    "name": "Probation Period",
                    "lookFor": "Probationary period:",
                    "type": "text",
                    "strategy": "first",
                    "validations": []
                }
            ],
            "validations": {}
        },
        "expected": {
            "Probation Period": "Three Months"
        }
    }
]


def run_test_scenario(scenario):
    """Run a single test scenario"""
    print(f"\n{'='*80}")
    print(f"TEST: {scenario['name']}")
    print(f"DESC: {scenario['description']}")
    print(f"{'='*80}")
    
    if not Path(PDF_PATH).exists():
        print(f"❌ SKIP: PDF file not found at {PDF_PATH}")
        return {"status": "skipped", "reason": "PDF not found"}
    
    try:
        # Submit validation request
        with open(PDF_PATH, 'rb') as f:
            files = {'files': f}
            data = {'rules': json.dumps(scenario['rules'])}
            
            print(f"📤 Submitting request...")
            response = requests.post(f"{BASE_URL}/api/v1/submit", files=files, data=data)
            
            if response.status_code != 200:
                print(f"❌ FAIL: HTTP {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return {"status": "failed", "reason": f"HTTP {response.status_code}"}
            
            result = response.json()
            task_id = result.get('task_id')
            print(f"✓ Task created: {task_id}")
            
            # Poll for completion
            print(f"⏳ Waiting for processing...")
            max_attempts = 30
            for attempt in range(max_attempts):
                time.sleep(1)
                status_response = requests.get(f"{BASE_URL}/api/v1/tasks/{task_id}")
                
                if status_response.status_code != 200:
                    continue
                
                status_data = status_response.json()
                state = status_data.get('state')
                
                if state == 'SUCCESS':
                    print(f"✓ Processing complete")
                    
                    # Get report
                    report_response = requests.get(f"{BASE_URL}/api/v1/tasks/{task_id}/report.json")
                    if report_response.status_code == 200:
                        report = report_response.json()
                        
                        # Verify results
                        if report.get('results') and len(report['results']) > 0:
                            file_result = report['results'][0]
                            extractions = file_result.get('validation_report', {}).get('extractions', {})
                            
                            print(f"\n📊 RESULTS:")
                            print(f"   Status: {file_result.get('Status')}")
                            print(f"   Signed: {file_result.get('Signed', 'N/A')}")
                            
                            # Check extracted fields
                            all_match = True
                            for expected_field, expected_value in scenario['expected'].items():
                                actual_value = extractions.get(expected_field, '')
                                match = actual_value == expected_value
                                symbol = "✓" if match else "✗"
                                
                                print(f"   {symbol} {expected_field}:")
                                print(f"      Expected: {expected_value}")
                                print(f"      Actual:   {actual_value}")
                                
                                if not match:
                                    all_match = False
                            
                            # Check validations
                            validations = file_result.get('validation_report', {}).get('validations', {})
                            if 'must_contain' in scenario['rules'].get('validations', {}):
                                contains_result = 'contains' in file_result.get('validation_report', {})
                                print(f"   {'✓' if contains_result else '✗'} Must contain check")
                            
                            if all_match:
                                print(f"\n✅ TEST PASSED")
                                return {"status": "passed", "extractions": extractions}
                            else:
                                print(f"\n⚠️ TEST FAILED - Extraction mismatch")
                                return {"status": "failed", "reason": "extraction mismatch", "extractions": extractions}
                        else:
                            print(f"❌ FAIL: No results in report")
                            return {"status": "failed", "reason": "no results"}
                    else:
                        print(f"❌ FAIL: Could not retrieve report")
                        return {"status": "failed", "reason": "no report"}
                
                elif state == 'FAILURE':
                    error = status_data.get('info', {}).get('error', 'Unknown error')
                    print(f"❌ FAIL: Processing failed - {error}")
                    return {"status": "failed", "reason": error}
                
                if attempt % 5 == 0:
                    print(f"   Still waiting... ({attempt}/{max_attempts})")
            
            print(f"❌ FAIL: Timeout waiting for results")
            return {"status": "failed", "reason": "timeout"}
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return {"status": "error", "reason": str(e)}


def main():
    """Run all test scenarios"""
    print("="*80)
    print(" VALIDO AUTOMATED EXTRACTION TEST SUITE")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"PDF Path: {PDF_PATH}")
    print(f"Total Scenarios: {len(TEST_SCENARIOS)}")
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/api/v1/network-info", timeout=5)
        print(f"✓ Server is running")
    except:
        print(f"❌ ERROR: Server is not running at {BASE_URL}")
        print(f"   Please start the server with: uvicorn app.main:app --reload")
        return
    
    # Run tests
    results = []
    for i, scenario in enumerate(TEST_SCENARIOS, 1):
        print(f"\n\n[{i}/{len(TEST_SCENARIOS)}]")
        result = run_test_scenario(scenario)
        results.append({
            "name": scenario["name"],
            "result": result
        })
        time.sleep(2)  # Brief pause between tests
    
    # Summary
    print(f"\n\n{'='*80}")
    print(" TEST SUMMARY")
    print(f"{'='*80}")
    
    passed = sum(1 for r in results if r['result']['status'] == 'passed')
    failed = sum(1 for r in results if r['result']['status'] == 'failed')
    skipped = sum(1 for r in results if r['result']['status'] == 'skipped')
    errors = sum(1 for r in results if r['result']['status'] == 'error')
    
    print(f"Total:   {len(results)}")
    print(f"✅ Passed:  {passed}")
    print(f"❌ Failed:  {failed}")
    print(f"⏭️  Skipped: {skipped}")
    print(f"⚠️  Errors:  {errors}")
    
    if failed > 0:
        print(f"\nFailed tests:")
        for r in results:
            if r['result']['status'] == 'failed':
                print(f"  - {r['name']}: {r['result'].get('reason', 'unknown')}")
    
    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    main()
