void charge(int *lamp)
{
    OCHU_TRACE_POINTER(lamp);
    *lamp = *lamp + 20;
    OCHU_TRACE_POINTER(lamp);
}
