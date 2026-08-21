"""Reading the form. Nothing here talks to GitHub."""

import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "add_rice", Path(__file__).resolve().parent.parent / "scripts" / "add_rice.py")
add_rice = importlib.util.module_from_spec(spec)
spec.loader.exec_module(add_rice)


FILLED_IN = """### Name

Serpantinum

### Repository

https://github.com/ilyamiro/serpantinum

### Screenshot

![shot](https://raw.githubusercontent.com/a/b/main/1.png)

### Description

Colours from your wallpaper.

### Distributions it is known to work on

- [X] arch
- [ ] fedora
- [x] nixos
"""


class TestReadingTheForm(unittest.TestCase):
    def setUp(self):
        self.form = add_rice.parse_form(FILLED_IN)

    def test_every_field_comes_through(self):
        self.assertEqual(self.form["name"], "Serpantinum")
        self.assertEqual(self.form["repository"], "https://github.com/ilyamiro/serpantinum")
        self.assertEqual(self.form["description"], "Colours from your wallpaper.")

    def test_only_ticked_boxes_count(self):
        chosen = add_rice.ticked(self.form["distributions it is known to work on"])
        self.assertEqual(chosen, ["arch", "nixos"])

    def test_a_field_left_empty_is_empty(self):
        form = add_rice.parse_form("### Name\n\n_No response_\n")
        self.assertEqual(form["name"], "")

    def test_windows_line_endings(self):
        form = add_rice.parse_form("### Name\r\n\r\nSerpantinum\r\n")
        self.assertEqual(form["name"], "Serpantinum")


class TestFindingTheImage(unittest.TestCase):
    PNG = "https://raw.githubusercontent.com/a/b/main/1.png"

    def test_an_image_dragged_into_the_box(self):
        dragged = "https://github.com/user-attachments/assets/8b7d2f10-4c3a"
        self.assertEqual(add_rice.first_image(f"![shot]({dragged})"), dragged)

    def test_a_link_pasted_on_its_own(self):
        self.assertEqual(add_rice.first_image(self.PNG), self.PNG)

    def test_a_link_with_a_sentence_around_it(self):
        self.assertEqual(add_rice.first_image(f"here it is: {self.PNG}."), self.PNG)

    def test_an_img_tag_copied_out_of_a_readme(self):
        self.assertEqual(
            add_rice.first_image(f'<img src="{self.PNG}" width="600">'), self.PNG)

    def test_nothing_to_find(self):
        self.assertEqual(add_rice.first_image("I do not have one"), "")
        self.assertEqual(add_rice.first_image(""), "")


class TestSplittingTheRepo(unittest.TestCase):
    def test_a_plain_address(self):
        self.assertEqual(add_rice.split_repo("https://github.com/end-4/dots-hyprland"),
                         ("end-4", "dots-hyprland"))

    def test_a_trailing_slash_and_dot_git(self):
        self.assertEqual(add_rice.split_repo("https://github.com/a/b.git/"), ("a", "b"))

    def assert_refused(self, url):
        with self.assertRaises(add_rice.Refused):
            add_rice.split_repo(url)

    def test_somewhere_else_entirely(self):
        self.assert_refused("https://evil.example/payload")

    def test_gitlab_is_left_to_a_person(self):
        self.assert_refused("https://gitlab.com/a/b")

    def test_a_user_page_is_not_a_repository(self):
        self.assert_refused("https://github.com/end-4")

    def test_characters_that_cannot_be_in_a_repository_name(self):
        self.assert_refused("https://github.com/a/b;touch /tmp/pwned")
        self.assert_refused("https://github.com/../../etc/passwd")


if __name__ == "__main__":
    unittest.main()
