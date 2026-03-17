"""
Markdown 简历解析模块
"""
import mistune
import re
from typing import Dict, List, Optional, Any


class ResumeParser:
    """Markdown 简历解析器"""
    
    def __init__(self):
        self.markdown = mistune.create_markdown(plugins=['table'])
    
    def parse(self, markdown_content: str) -> Dict[str, Any]:
        """
        解析 Markdown 简历
        
        Args:
            markdown_content: Markdown 格式的简历内容
            
        Returns:
            结构化简历信息字典
        """
        lines = markdown_content.strip().split('\n')
        
        return {
            'name': self._extract_name(lines),
            'email': self._extract_email(markdown_content),
            'phone': self._extract_phone(markdown_content),
            'skills': self._extract_skills(lines),
            'experience': self._extract_experience(lines),
            'education': self._extract_education(lines),
            'summary': self._extract_summary(lines),
            'raw_content': markdown_content
        }
    
    def _extract_name(self, lines: List[str]) -> Optional[str]:
        """提取姓名（通常在第一个标题）"""
        for line in lines[:5]:
            line = line.strip()
            # 移除#标记
            if line.startswith('#'):
                line = re.sub(r'^#+\s*', '', line)
            if line and len(line) < 20:  # 姓名通常较短
                return line
        return None
    
    def _extract_email(self, text: str) -> Optional[str]:
        """提取邮箱"""
        match = re.search(r'[\w.-]+@[\w.-]+\.\w+', text)
        return match.group() if match else None
    
    def _extract_phone(self, text: str) -> Optional[str]:
        """提取手机号"""
        match = re.search(r'1[3-9]\d{9}', text)
        return match.group() if match else None
    
    def _extract_skills(self, lines: List[str]) -> List[str]:
        """提取技能列表"""
        skills = []
        in_skills_section = False
        
        for line in lines:
            line_lower = line.lower()
            
            # 检测技能部分
            if any(kw in line_lower for kw in ['技能', 'skill', '技术栈', 'tech stack']):
                if '#' in line or '##' in line:
                    in_skills_section = True
                    continue
            
            if in_skills_section:
                # 遇到新章节结束
                if line.startswith('#') and not line.strip().startswith('###'):
                    break
                
                # 解析技能项
                if line.strip():
                    # 处理逗号、顿号分隔
                    items = re.split(r'[,,/,]', line)
                    for item in items:
                        item = item.strip().strip('•-–—')
                        if item and len(item) < 50:
                            skills.append(item)
        
        return list(set(skills))
    
    def _extract_experience(self, lines: List[str]) -> List[Dict[str, Any]]:
        """提取工作经历"""
        experience = []
        current_exp = {}
        in_experience = False
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            
            # 检测工作经历部分
            if any(kw in line_lower for kw in ['经历', 'experience', '工作', 'work']):
                if '#' in line or '##' in line:
                    in_experience = True
                    continue
            
            if in_experience:
                # 检测公司/职位标题
                if '###' in line or '**' in line:
                    if current_exp:
                        experience.append(current_exp)
                    current_exp = {
                        'title': self._clean_line(line),
                        'company': '',
                        'duration': '',
                        'responsibilities': []
                    }
                elif current_exp:
                    # 检测时间
                    time_match = re.search(r'\d{4}[-/.]\d{4}|\d{4}[-/.] 至今', line)
                    if time_match and not current_exp.get('duration'):
                        current_exp['duration'] = time_match.group()
                    elif line.strip():
                        current_exp['responsibilities'].append(self._clean_line(line))
        
        if current_exp:
            experience.append(current_exp)
        
        return experience
    
    def _extract_education(self, lines: List[str]) -> List[Dict[str, Any]]:
        """提取教育经历"""
        education = []
        current_edu = {}
        in_education = False
        
        for line in lines:
            line_lower = line.lower()
            
            # 检测教育部分
            if any(kw in line_lower for kw in ['教育', 'education', '学历', '学校']):
                if '#' in line or '##' in line:
                    in_education = True
                    continue
            
            if in_education:
                if '###' in line or '**' in line:
                    if current_edu:
                        education.append(current_edu)
                    current_edu = {
                        'school': self._clean_line(line),
                        'degree': '',
                        'duration': ''
                    }
                elif current_edu:
                    time_match = re.search(r'\d{4}[-/.]\d{4}|\d{4}[-/.] 至今', line)
                    if time_match:
                        current_edu['duration'] = time_match.group()
                    elif line.strip() and not current_edu.get('degree'):
                        current_edu['degree'] = self._clean_line(line)
        
        if current_edu:
            education.append(current_edu)
        
        return education
    
    def _extract_summary(self, lines: List[str]) -> Optional[str]:
        """提取个人简介"""
        in_summary = False
        summary_lines = []
        
        for line in lines:
            line_lower = line.lower()
            
            if any(kw in line_lower for kw in ['简介', 'summary', '关于', 'about']):
                if '#' in line or '##' in line:
                    in_summary = True
                    continue
            
            if in_summary:
                if line.startswith('#'):
                    break
                if line.strip():
                    summary_lines.append(self._clean_line(line))
        
        return '\n'.join(summary_lines) if summary_lines else None
    
    def _clean_line(self, line: str) -> str:
        """清理行内容，移除 Markdown 标记"""
        line = re.sub(r'^#+\s*', '', line)
        line = re.sub(r'\*\*|\*', '', line)
        line = re.sub(r'^[-•]\s*', '', line)
        return line.strip()
    
    def format_for_prompt(self, resume_data: Dict[str, Any]) -> str:
        """
        格式化为 Prompt 注入文本
        
        Args:
            resume_data: 解析后的简历数据
            
        Returns:
            格式化的简历文本
        """
        parts = []
        
        if resume_data.get('name'):
            parts.append(f"姓名：{resume_data['name']}")
        if resume_data.get('email'):
            parts.append(f"邮箱：{resume_data['email']}")
        if resume_data.get('phone'):
            parts.append(f"电话：{resume_data['phone']}")
        
        if resume_data.get('summary'):
            parts.append(f"\n个人简介:\n{resume_data['summary']}")
        
        if resume_data.get('skills'):
            parts.append(f"\n技能:\n{', '.join(resume_data['skills'])}")
        
        if resume_data.get('experience'):
            parts.append("\n工作经历:")
            for exp in resume_data['experience']:
                parts.append(f"- {exp.get('title', '')}")
                for resp in exp.get('responsibilities', []):
                    parts.append(f"  • {resp}")
        
        if resume_data.get('education'):
            parts.append("\n教育背景:")
            for edu in resume_data['education']:
                parts.append(f"- {edu.get('school', '')} {edu.get('degree', '')} {edu.get('duration', '')}")
        
        return '\n'.join(parts)


def parse_resume(markdown_path: str) -> Dict[str, Any]:
    """
    便捷函数：从文件解析简历
    
    Args:
        markdown_path: Markdown 简历文件路径
        
    Returns:
        结构化简历信息
    """
    with open(markdown_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    parser = ResumeParser()
    return parser.parse(content)
