void charge(int *target)
{
    OCHU_TRACE_POINTER(target);
    *target += 20;
    OCHU_TRACE_POINTER(target);
}
