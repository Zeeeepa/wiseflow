# WiseFlow Documentation Standards

This document defines the standards for WiseFlow documentation to ensure consistency, clarity, and maintainability across all documentation files.

## General Principles

1. **Clarity**: Documentation should be clear, concise, and easy to understand
2. **Completeness**: Documentation should cover all relevant aspects of the topic
3. **Accuracy**: Documentation should accurately reflect the current state of the codebase
4. **Consistency**: Documentation should use consistent terminology, formatting, and structure
5. **Accessibility**: Documentation should be accessible to users with different levels of expertise

## Document Structure

Each documentation file should include the following sections:

1. **Title**: A clear, descriptive title that indicates the topic
2. **Overview**: A brief introduction that explains the purpose and scope of the document
3. **Prerequisites**: Any prerequisites or dependencies required to follow the document
4. **Main Content**: The main content of the document, organized into logical sections
5. **Examples**: Practical examples that illustrate the concepts described
6. **Troubleshooting**: Common issues and their solutions
7. **Related Topics**: Links to related documentation
8. **Version Information**: Information about which versions of the software the document applies to

## Formatting Guidelines

### Markdown Usage

All documentation should be written in Markdown and follow these formatting guidelines:

1. **Headings**: Use ATX-style headings (with `#` symbols)
   - Level 1 (`#`) for document title
   - Level 2 (`##`) for main sections
   - Level 3 (`###`) for subsections
   - Level 4 (`####`) for sub-subsections

2. **Lists**: Use unordered lists (with `-` or `*`) for items without sequence, and ordered lists (with `1.`, `2.`, etc.) for sequential items

3. **Code Blocks**: Use fenced code blocks with language specification
   ```python
   # Python code example
   def example_function():
       return "Hello, World!"
   ```

4. **Inline Code**: Use backticks for inline code references, e.g., `config.json`

5. **Links**: Use reference-style links for better readability in the source
   ```markdown
   [Link text][reference]

   [reference]: https://example.com
   ```

6. **Images**: Include alt text for all images
   ```markdown
   ![Alt text](path/to/image.png "Optional title")
   ```

7. **Tables**: Use tables for structured data
   ```markdown
   | Header 1 | Header 2 |
   |----------|----------|
   | Cell 1   | Cell 2   |
   ```

8. **Emphasis**: Use *italics* for emphasis and **bold** for strong emphasis

9. **Blockquotes**: Use blockquotes for notes, warnings, or quotes
   ```markdown
   > Note: This is an important note.
   ```

10. **Horizontal Rules**: Use horizontal rules to separate major sections
    ```markdown
    ---
    ```

### Special Formatting

1. **Notes and Warnings**: Use blockquotes with special prefixes
   ```markdown
   > **Note:** This is an important note.

   > **Warning:** This is a warning.
   ```

2. **API Endpoints**: Format API endpoints consistently
   ```markdown
   `GET /api/v1/focus-points`
   ```

3. **File Paths**: Format file paths consistently
   ```markdown
   `path/to/file.ext`
   ```

4. **Command-Line Examples**: Include the command prompt in command-line examples
   ```markdown
   ```bash
   $ python -m core.app
   ```
   ```

## Content Guidelines

### Language and Style

1. **Voice**: Use active voice and present tense
2. **Audience**: Write for the intended audience (users, administrators, developers)
3. **Terminology**: Use consistent terminology throughout the documentation
4. **Abbreviations**: Define abbreviations on first use
5. **Jargon**: Avoid jargon or explain technical terms
6. **Examples**: Provide realistic, practical examples
7. **Step-by-Step Instructions**: Break down complex procedures into clear steps

### Code Examples

1. **Completeness**: Ensure code examples are complete and can be run as-is
2. **Context**: Provide context for code examples
3. **Comments**: Include comments to explain key parts of the code
4. **Best Practices**: Follow best practices in code examples
5. **Error Handling**: Include error handling in code examples
6. **Output**: Show expected output where relevant

### Screenshots and Diagrams

1. **Relevance**: Include screenshots and diagrams only when they add value
2. **Resolution**: Use high-resolution images
3. **Annotations**: Annotate screenshots to highlight important elements
4. **Alt Text**: Provide descriptive alt text for all images
5. **Consistency**: Use consistent visual style for diagrams

## Multilingual Documentation

1. **Base Language**: English is the base language for all documentation
2. **Translations**: Translations should be as close as possible to the original
3. **Cultural Considerations**: Be aware of cultural differences in translations
4. **Technical Terms**: Keep technical terms consistent across languages
5. **Language Indicators**: Clearly indicate the language of each document

## Documentation Maintenance

1. **Version Control**: All documentation changes should be tracked in version control
2. **Review Process**: Documentation changes should be reviewed for accuracy and adherence to standards
3. **Update Frequency**: Documentation should be updated whenever related code changes
4. **Deprecation**: Clearly mark deprecated features in documentation
5. **Archiving**: Archive documentation for older versions rather than deleting it

## Documentation Testing

1. **Link Checking**: Regularly check for broken links
2. **Code Testing**: Test code examples to ensure they work as described
3. **Spelling and Grammar**: Check spelling and grammar in all documentation
4. **Accessibility Testing**: Test documentation for accessibility issues
5. **User Testing**: Gather feedback from users on documentation clarity and completeness

## Implementation Checklist

When creating or updating documentation, use this checklist:

- [ ] Document follows the standard structure
- [ ] Formatting adheres to guidelines
- [ ] Content is clear, accurate, and complete
- [ ] Code examples are tested and working
- [ ] Links are valid and point to the correct destinations
- [ ] Images have alt text and are appropriately sized
- [ ] Spelling and grammar are correct
- [ ] Document is accessible to the intended audience
- [ ] Version information is included
- [ ] Related documents are linked
- [ ] Document is available in all supported languages

