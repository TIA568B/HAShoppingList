# Requirements: Categorized Alexa Shopping List

## Overview
A Home Assistant feature that presents the Alexa-synced shopping list (`todo.shopping_list`)
grouped into categories (e.g. Milk, Chilled, Bakery, Produce, Household), initially derived from
the user's historical shopping list data, with a reactive check-off UI (including undo) that
stays in sync with the original Alexa list.

Note: the user is vegan, so egg and other animal-derived categories/keywords must be excluded
from the initial categorization model. Milk-keyword items get their own "Milk" category. Other
dairy-style items (cheese, yogurt, butter, cream) go under "Chilled" rather than a dedicated
dairy category. Both are assumed to be non-dairy given the user is vegan. Meat-keyword items
(e.g. "sausages", "bacon", "mince") are assumed to be plant-based substitutes and SHALL be
categorized as "Fake Meat" rather than excluded.

---

## Requirement 1: Historical Categorization Bootstrap

**User Story:** As a user, I want the system to analyze my past shopping list items so that my
categories are pre-populated and relevant to what I actually buy, instead of starting from an
empty or generic template.

### Acceptance Criteria
1. WHEN the feature is first set up THE SYSTEM SHALL read available historical shopping list
   data (e.g. HA history/logbook for `todo.shopping_list`, or a user-supplied export) to build
   an initial item-to-category mapping.
2. WHEN building the initial mapping THE SYSTEM SHALL exclude egg and other animal-derived
   categories and keywords (i.e. non-vegan items, excluding milk/dairy-style and meat items per
   Requirements 3 and 4) from the generated category set.
3. WHEN an historical or new item matches a milk-related keyword (e.g. "milk", "oat milk", "soy
   milk") THE SYSTEM SHALL categorize it under its own "Milk" category, on the assumption that it
   refers to a plant-based/non-dairy product.
4. WHEN an historical or new item matches a chilled dairy-style keyword (e.g. "cheese",
   "yogurt", "butter", "cream") THE SYSTEM SHALL categorize it under "Chilled" rather than a
   dedicated dairy category, on the assumption that it refers to a plant-based/non-dairy product.
5. WHEN an historical or new item matches a meat-related keyword (e.g. "sausages", "bacon",
   "mince", "chicken pieces") THE SYSTEM SHALL categorize it under "Fake Meat" rather than
   excluding it, on the assumption that it refers to a plant-based substitute.
6. WHEN an historical item cannot be confidently mapped to a category THE SYSTEM SHALL place it
   in an "Uncategorized" bucket rather than guessing.
7. WHEN the historical bootstrap completes THE SYSTEM SHALL present the generated
   category/keyword mapping to the user for review before it is used live.
8. IF no historical data is available THE SYSTEM SHALL fall back to a small default category set
   of vegan-appropriate categories (e.g. Produce, Bakery, Milk, Chilled, Fake Meat, Household,
   Other) and SHALL NOT block setup.

## Requirement 2: Ongoing Item Categorization

**User Story:** As a user, I want new items added to the Alexa list to be categorized
automatically so I never have to manually sort day-to-day.

### Acceptance Criteria
1. WHEN a new item is added to `todo.shopping_list` THE SYSTEM SHALL attempt to match it against
   the category/keyword mapping within a reactive delay of no more than a few seconds.
2. WHEN an item matches a known keyword THE SYSTEM SHALL assign it to the corresponding category.
3. WHEN an item does not match any known keyword THE SYSTEM SHALL assign it to "Uncategorized"
   and SHALL make it easy for the user to manually assign a category from the UI.
4. WHEN the user manually assigns or corrects an item's category THE SYSTEM SHALL persist that
   mapping so future identical items are categorized the same way automatically.

## Requirement 3: Reactive Display

**User Story:** As a user, I want the categorized list to update live as I interact with it, so
the UI always reflects the current state of my list without manual refresh.

### Acceptance Criteria
1. WHEN the underlying `todo.shopping_list` entity changes (item added, removed, or completed by
   any source, including Alexa directly) THE SYSTEM SHALL update the displayed categorized view
   without requiring a manual page refresh.
2. WHEN the user ticks an item off in the categorized view THE SYSTEM SHALL immediately reflect
   the item as checked in the UI (optimistic update) before the backend sync completes.
3. WHEN a category has zero remaining unchecked items THE SYSTEM SHALL visually collapse or
   de-emphasize that category so the user can focus on what's left.

## Requirement 4: Tick-Off with Undo

**User Story:** As a user, I want to tick items off quickly but be able to undo a mistaken
tick-off easily, so I don't accidentally lose items while shopping.

### Acceptance Criteria
1. WHEN the user ticks an item off THE SYSTEM SHALL mark it as completed in the UI and start a
   short grace period (target: 8-10 seconds) before the completion is finalized.
2. WHILE the grace period is active THE SYSTEM SHALL display an undo control for that specific
   item.
3. WHEN the user selects undo within the grace period THE SYSTEM SHALL restore the item to its
   unchecked state in both the UI and, if already sent, reverse the change on
   `todo.shopping_list`.
4. WHEN the grace period expires without undo THE SYSTEM SHALL finalize the completion and sync
   it to `todo.shopping_list`.
5. IF the user ticks off multiple items in quick succession THE SYSTEM SHALL track undo state
   independently per item.

## Requirement 5: Sync Back to Alexa List

**User Story:** As a user, I want any changes I make in the categorized view (ticking items,
adding items, undoing) to reflect back on the original Alexa shopping list, so both stay
consistent regardless of which one I use.

### Acceptance Criteria
1. WHEN an item is completed (post grace-period) in the categorized view THE SYSTEM SHALL call
   the appropriate HA `todo` service to mark/remove the corresponding item on
   `todo.shopping_list`.
2. WHEN an item is added via the categorized view THE SYSTEM SHALL add it to
   `todo.shopping_list` using the existing native HA todo services.
3. WHEN an item is completed or added directly via Alexa (outside the categorized view) THE
   SYSTEM SHALL reflect that change in the categorized view per Requirement 3.
4. IF a sync call to `todo.shopping_list` fails THE SYSTEM SHALL retry and SHALL surface a
   visible error/warning to the user rather than silently dropping the change.

## Requirement 6: Category Maintenance

**User Story:** As a user, I want to be able to view and edit the category set and keyword
mappings over time, so the system stays accurate as my shopping habits change.

### Acceptance Criteria
1. WHEN the user opens category settings THE SYSTEM SHALL display all categories and their
   associated keywords.
2. WHEN the user adds, edits, or removes a category or keyword THE SYSTEM SHALL persist the
   change and apply it to future categorization immediately.
3. WHEN a category is deleted THE SYSTEM SHALL reassign its items to "Uncategorized" rather than
   deleting the items themselves.
