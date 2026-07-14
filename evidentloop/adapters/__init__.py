"""Input adapters for supported audit profiles."""

from .gitdiff import GitDiffBundle, GitDiffCollectionError, collect_git_diff

__all__ = ["GitDiffBundle", "GitDiffCollectionError", "collect_git_diff"]
