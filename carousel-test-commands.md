# Carousel Reposition Testing Commands

## Console Commands for Testing Carousel Repositioning

After loading a page with carousels, open the browser console and try these commands:

### 1. Debug a specific carousel
```javascript
// Debug the category carousel
debugCarousel('categoryCarousel');

// Debug the lesson carousel  
debugCarousel('lessonCarousel');
```

### 2. Reposition a specific carousel
```javascript
// Fix the category carousel if it appears flat
repositionCarousel('categoryCarousel');

// Fix the lesson carousel if it appears flat
repositionCarousel('lessonCarousel');
```

### 3. Reposition all carousels on the page
```javascript
// Fix all carousels at once
repositionAllCarousels();
```

### 4. Direct method calls (if you have carousel reference)
```javascript
// If you have direct access to carousel instance
window.categoryCarousel.reposition();
window.lessonCarousel.reposition();
```

## What the reposition method does:

1. **Recalculates card dimensions** - Gets fresh offsetWidth measurements
2. **Recalculates radius** - Uses the same formula as initial load but with current dimensions
3. **Reapplies transforms** - Sets new `rotateY()` and `translateZ()` values for each card
4. **Handles hidden elements** - Temporarily shows hidden carousels to get accurate measurements
5. **Preserves state** - Maintains current rotation and selected cards
6. **Logs detailed info** - Shows calculations and results in console

## Common scenarios where reposition is needed:

- Carousel appears flat (all cards in a line)
- Cards are too close together or overlapping
- After window resize or layout changes
- After showing/hiding carousel containers
- When carousel was initialized while hidden

## Expected console output:
```
🔄 Repositioning carousel "categoryCarousel"...
Card width: 280px, Item count: 6
Calculated radius: 280.50px, Min radius: 181.33px, Final radius: 400px
Card 0: angle=0deg, transform=rotateY(0deg) translateZ(400px)
Card 1: angle=60deg, transform=rotateY(60deg) translateZ(400px)
...
✅ Carousel "categoryCarousel" repositioned successfully
```
