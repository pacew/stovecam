#ifdef __cplusplus
extern "C"
{
#endif

	void i2c_init (void);
	int i2c_general_reset (void);
	void i2c_frequency(int);
	int i2c_read (uint8_t, uint16_t, uint16_t, uint16_t *);
	int i2c_write (uint8_t, uint16_t, uint16_t);

#ifdef __cplusplus
}
#endif
