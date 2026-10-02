#include <stdio.h>
#include <stdlib.h>

static void snapshot(const char *phase, int *inventory, size_t slots)
{
    printf("{\"event\":\"inventory\",\"phase\":\"%s\","
           "\"block_address\":\"%p\",\"slots\":%zu,\"values\":[",
           phase, (void *)inventory, slots);
    for (size_t i = 0; i < slots; ++i)
        printf("%s%d", i ? "," : "", inventory[i]);
    puts("]}");
}

int main(void)
{
    size_t slots = 3;
    int *inventory = malloc(slots * sizeof *inventory);
    if (inventory == NULL) return EXIT_FAILURE;
    printf("{\"event\":\"allocation\",\"allocator\":\"malloc\","
           "\"block_address\":\"%p\",\"element_bytes\":%zu,"
           "\"requested_bytes\":%zu,\"contents\":\"uninitialized\"}\n",
           (void *)inventory, sizeof *inventory, slots * sizeof *inventory);
    /* Establish values before the first read. */
    for (size_t i = 0; i < slots; ++i)
        inventory[i] = (int)(101 + i);
    snapshot("initialized", inventory, slots);

    size_t new_slots = 5;
    int *resized = realloc(inventory, new_slots * sizeof *inventory);
    if (resized == NULL) {
        /* The original allocation remains owned and usable on failure. */
        free(inventory);
        return EXIT_FAILURE;
    }
    inventory = resized;
    for (size_t i = slots; i < new_slots; ++i)
        inventory[i] = 0;
    slots = new_slots;
    snapshot("resized_and_initialized", inventory, slots);

    /* Preserve text for the trace before the object lifetime ends. */
    char released_address[64];
    snprintf(released_address, sizeof released_address, "%p", (void *)inventory);
    free(inventory);
    inventory = NULL;
    printf("{\"event\":\"release\",\"block_address\":\"%s\","
           "\"pointer_value\":null,\"status\":\"freed\"}\n",
           released_address);
    return EXIT_SUCCESS;
}
