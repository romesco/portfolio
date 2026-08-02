---
title: ADA
description: "The UW's assistive-feeding robot (ADA) gets tested outside the lab (Personal Robotics Lab, 2025)."
head: |
  <style>
    /* /ADA is a full-screen theater for one video: black out the page,
       let the player own the viewport, and float the backlink + the
       UW News story link above it as unobtrusive pills. */
    body { background: #000; }
    .ada-player {
      position: fixed;
      inset: 0;
      width: 100%;
      height: 100%;
      border: 0;
      background: #000;
      z-index: 10;
    }
    .backlink { position: fixed; top: .75rem; left: .75rem; z-index: 20; margin: 0; }
    .backlink a,
    .story-link a {
      background: rgba(0, 0, 0, .55);
      color: #fff;
      padding: .25rem .6rem;
      border-radius: 999px;
      text-decoration: none;
      opacity: .5;
      transition: opacity .2s ease;
    }
    .backlink a:hover, .backlink a:focus-visible,
    .story-link a:hover, .story-link a:focus-visible { opacity: 1; }
    .story-link { position: fixed; top: .75rem; right: .75rem; z-index: 20; margin: 0; }
    .site-footer { display: none; }
  </style>
---

<iframe class="ada-player"
  src="https://www.youtube-nocookie.com/embed/Ul0KC6tZc4o?rel=0"
  title="The UW's assistive-feeding robot gets tested outside the lab (University of Washington, YouTube)"
  allow="autoplay; fullscreen; picture-in-picture; clipboard-write; encrypted-media"
  allowfullscreen
  referrerpolicy="strict-origin-when-cross-origin"></iframe>

<p class="story-link"><a href="https://www.washington.edu/news/2025/03/04/assistive-feeding-robot-gets-tested-outside-the-lab/"
  target="_blank" rel="noopener"
  title="Read the UW News story: Assistive-feeding robot gets tested outside the lab">UW News ↗</a></p>
