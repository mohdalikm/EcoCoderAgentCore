#!/usr/bin/env python3
"""
Test script for the LLM Code Reviewer
"""
import sys
import os

# Add the project root to the path
sys.path.insert(0, '/Users/ali/Source/EcoCoderAgentCore')

from app.tools.llm_code_reviewer import analyze_code_quality_with_llm

def test_llm_code_reviewer():
    """Test the LLM code reviewer with a real PR"""
    
    # Sample PR payload with diff_url
    pr_payload = {
        "action": "opened",
        "number": 1,
        "pull_request": {
            "number": 1,
            "title": "Test PR with LLM Code Review",
            "body": "Testing the new LLM-based code reviewer",
            "diff_url": "https://github.com/mohdalikm/test-repo/pull/1.diff",
            "head": {
                "ref": "change-1",
                "sha": "4df3c1de74516fcb5c285e302c00fa12f26d01eb"
            },
            "base": {
                "ref": "main",
                "sha": "f42a04fe075da35f420bd7b6845464a9b5632f74"
            },
            "additions": 447068,
            "deletions": 1,
            "changed_files": 272
        },
        "repository": {
            "name": "test-repo",
            "full_name": "mohdalikm/test-repo",
            "clone_url": "https://github.com/mohdalikm/test-repo.git",
            "owner": {
                "login": "mohdalikm",
                "id": "12345"
            }
        }
    }
    
    print("🔍 Testing LLM Code Reviewer...")
    print("=" * 50)
    
    try:
        # Test the LLM code reviewer
        result = analyze_code_quality_with_llm(
            repository_arn="arn:aws:codecommit:ap-southeast-1:12345:mohdalikm/test-repo",
            branch_name="change-1",
            commit_sha="4df3c1de74516fcb5c285e302c00fa12f26d01eb",
            pr_payload=pr_payload,
            github_token=None  # Will fetch from secrets
        )
        
        print(f"✅ Analysis Status: {result.get('status', 'unknown')}")
        print(f"✅ Analysis Type: {result.get('analysis_type', 'unknown')}")
        print(f"✅ Total Findings: {result.get('total_findings', 0)}")
        print(f"✅ Files Analyzed: {result.get('files_analyzed', 0)}")
        print(f"✅ Lines Changed: {result.get('lines_changed', 0)}")
        print(f"✅ Languages: {result.get('languages', [])}")
        print(f"✅ Analysis Time: {result.get('analysis_time_seconds', 0):.2f} seconds")
        
        # Show some findings if available
        findings = result.get('findings', [])
        if findings:
            print(f"\n📋 Sample Findings (showing first 3):")
            for i, finding in enumerate(findings[:3]):
                severity = finding.get('severity', 'unknown').upper()
                category = finding.get('category', 'unknown')
                title = finding.get('title', 'N/A')
                print(f"  {i+1}. [{severity}] {category}: {title}")
        
        # Show recommendations if available
        recommendations = result.get('recommendations', [])
        if recommendations:
            print(f"\n💡 Recommendations (showing first 3):")
            for i, rec in enumerate(recommendations[:3]):
                print(f"  {i+1}. {rec}")
        
        print(f"\n🎉 LLM Code Reviewer test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_llm_code_reviewer()
    sys.exit(0 if success else 1)