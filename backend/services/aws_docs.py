import re
import logging
import requests
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class AWSProviderDocsFetcher:
    """Fetches real-time documentation from Terraform AWS Provider registry"""

    def __init__(self):
        self.base_url = "https://registry.terraform.io/providers/hashicorp/aws/latest/docs"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def fetch_resource_docs(self, resource_type: str) -> Optional[Dict[str, Any]]:
        """Fetch documentation for a specific AWS resource type"""
        try:
            resource_name = resource_type.replace('aws_', '')
            url = f"{self.base_url}/resources/{resource_name}"

            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch docs for {resource_type}: {response.status_code}")
                return None

            soup = BeautifulSoup(response.content, 'html.parser')

            return {
                'resource_type': resource_type,
                'url': url,
                'arguments': self._extract_arguments(soup),
                'example': self._extract_example(soup),
                'required_args': self._extract_required_arguments(soup),
                'optional_args': self._extract_optional_arguments(soup)
            }

        except Exception as e:
            logger.error(f"Error fetching docs for {resource_type}: {e}")
            return None

    def _extract_arguments(self, soup: BeautifulSoup) -> List[str]:
        arguments = []
        arg_sections = soup.find_all(['h3', 'h4'], string=re.compile(r'Arguments?|Parameters?'))
        for section in arg_sections:
            next_list = section.find_next_sibling(['ul', 'dl'])
            if next_list:
                for item in next_list.find_all(['li', 'dt']):
                    code_tag = item.find('code')
                    if code_tag:
                        arg_name = code_tag.get_text().strip()
                        if arg_name and not arg_name.startswith('('):
                            arguments.append(arg_name)
        return list(set(arguments))

    def _extract_required_arguments(self, soup: BeautifulSoup) -> List[str]:
        required_args = []
        for element in soup.find_all(text=re.compile(r'\(Required\)|required|Required')):
            parent = element.parent
            if parent:
                code_tag = parent.find('code') or parent.find_previous('code')
                if code_tag:
                    arg_name = code_tag.get_text().strip()
                    if arg_name:
                        required_args.append(arg_name)
        return list(set(required_args))

    def _extract_optional_arguments(self, soup: BeautifulSoup) -> List[str]:
        optional_args = []
        for element in soup.find_all(text=re.compile(r'\(Optional\)|optional|Optional')):
            parent = element.parent
            if parent:
                code_tag = parent.find('code') or parent.find_previous('code')
                if code_tag:
                    arg_name = code_tag.get_text().strip()
                    if arg_name:
                        optional_args.append(arg_name)
        return list(set(optional_args))

    def _extract_example(self, soup: BeautifulSoup) -> Optional[str]:
        try:
            example_sections = soup.find_all(['h2', 'h3'], string=re.compile(r'Example|Usage'))
            for section in example_sections:
                code_block = section.find_next('pre') or section.find_next('code')
                if code_block:
                    example_code = code_block.get_text().strip()
                    if 'resource "' in example_code and len(example_code) > 50:
                        return example_code
            return None
        except Exception as e:
            logger.error(f"Error extracting example: {e}")
            return None
